---
category: middleware
excerpt: 'Redis Memory Hit 99.98% in Production and Triggered Eviction Alerts: How
  We Precisely Cleaned Up 50% of Cold Data Using LRU Idle Time to Free 4GB of Memory,
  and a Postmortem on the Architectural Risks Behind It'
keywords: redis, elasticache, oom, eviction, lru, idletime, architecture
lang: en
layout: post
title: 'An Emergency Production Incident: Redis Memory Exhaustion, Precise Cleanup,
  and an Architectural Postmortem'
---

## Introduction

Today I received a monitoring alert: memory usage on the primary Redis instance in production had spiked straight to **99.98%**, and `Evictions` on the dashboard had started climbing continuously.

Once this metric fires, it’s actually pretty dangerous, because this instance is configured with the `allkeys-lru` eviction policy. In other words, once memory is completely full, Redis will start randomly evicting old keys using the LRU strategy so it can keep accepting new writes. But this Redis instance is also serving user sessions, API rate-limit counters, and some foundational business caches. If I just let it keep evicting keys indiscriminately like this, it would only be a matter of time before critical business data got taken out by mistake.

Since I had confirmed Redis was indeed full, the first step definitely wasn’t to panic-delete things at random. I needed to first understand the situation clearly: **analyze memory usage distribution -> identify the biggest consumer -> design a safe cleanup plan -> eliminate the underlying risk**.

So here’s a write-up of this investigation process, the practical script I used to precisely clean up 50% of the data based on hit patterns, and a few architectural issues that surfaced during the postmortem.

<img src="https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260821235633107.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80" alt="QQ_1787374585754" style="zoom:25%;" />

<center>(Image placeholder: a CloudWatch / Datadog dashboard showing Redis memory hitting 100% and Evictions starting to increase)</center><br>

## 1. No Guessing in Production: Analyze Memory Distribution Across the Entire Keyspace

When dealing with a production Redis that’s completely full, the number one taboo is deleting keys based on gut feeling. The number two taboo is taking the “easy” route and running `KEYS *` or `FLUSHDB` directly (`KEYS *` can block the single-threaded server hard, and `FLUSHDB` can take down all online traffic immediately).

I had to first figure out what was actually consuming the memory. So I wrote a lightweight Python script that uses `SCAN` cursors to iterate through the entire keyspace in batches, sampling and estimating key counts and memory usage by prefix.

At the time, the memory distribution across the whole database looked roughly like this (sensitive business prefixes have been masked):

| Key Prefix (masked) | Key Count | Share by Count | Avg per Key | Estimated Memory Usage | Business Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`prod:search_emb:*`** | **585k** | **22.8%** | **14.5 KB** | **~8.07 GB (87.5%)** | 🔴 **Search query vector cache** |
| `prod:img_url:*` | 1.063M | 41.4% | 537 B | ~544 MB (5.9%) | Presigned image URL cache |
| `service_go:prod:*` | 188k | 7.3% | 1.95 KB | ~350 MB (3.8%) | Microservice acceleration cache |
| `prod:card_cache:*` | 38k | 1.5% | 2.03 KB | ~72.7 MB (0.8%) | Operations card cache |
| `prod:session:*` | 428k | 16.7% | 136 B | ~55.5 MB (0.6%) | User session state |
| `prod:qclass:*` | 171k | 6.7% | 211 B | ~34.4 MB (0.4%) | Classification tagging cache |
| `prod:user:*` / `LIMITS:*` | ~30k | 1.2% | 100~400 B | ~15 MB | User info, rate limiting, and other core business data |

Once I saw this table, the case was basically solved on the spot:
the entire Redis instance only had about **9.2 GB** of usable memory, and **`prod:search_emb:*` alone was consuming 8.07 GB (87.5%)**! Sessions, rate limiting, and other core business data were actually taking up only a tiny fraction. They were simply getting squeezed out by this one giant memory hog.

Here’s the non-blocking script I used to analyze the full keyspace distribution:

```python
import redis

r = redis.Redis(host="your-redis-host", port=6379, socket_timeout=10)

cursor = 0
stats = {}

while True:
    cursor, keys = r.scan(cursor=cursor, count=5000)
    for k in keys:
        k_str = k.decode("utf-8", errors="replace")
        parts = k_str.split(":")
        prefix = parts[0] + ":" + parts[1] if len(parts) >= 2 else parts[0]
        
        if prefix not in stats:
            stats[prefix] = {"count": 0, "sample_bytes": 0, "sample_cnt": 0}
        
        stats[prefix]["count"] += 1
        if stats[prefix]["sample_cnt"] < 50:
            m = r.memory_usage(k)
            if m:
                stats[prefix]["sample_bytes"] += m
                stats[prefix]["sample_cnt"] += 1
    if cursor == 0:
        break

total_keys = sum(s["count"] for s in stats.values())
print(f"Total keys: {total_keys}")
for p, s in sorted(stats.items(), key=lambda x: x[1]["count"] * (x[1]["sample_bytes"]/max(1, x[1]["sample_cnt"])), reverse=True):
    avg_m = s["sample_bytes"] / max(1, s["sample_cnt"])
    est_mb = (s["count"] * avg_m) / (1024 * 1024)
    print(f"{p:<30} | {s['count']:>8} | {avg_m:>8.1f}B | {est_mb:>10.2f} MB")
```

## 2. Check the Code: Can This Biggest Consumer Be Cleaned Up?

After identifying the prefix, I immediately went to the codebase to inspect the corresponding implementation.

It turned out this was used for semantic search: caching the 1024-dimensional embedding vectors generated by an LLM for user search queries.

The logic in the code followed a standard **Read-Through** pattern:
1. A user enters a search query, and the system first checks Redis to see whether the query’s embedding is already there;
2. If it’s a hit (Cache Hit), it directly uses the stored vector to query the vector database;
3. If it’s a miss (Cache Miss), it calls the LLM API to generate the 1024-dimensional vector, then writes it back to Redis with a **3-day (`ex=3*86400`)** TTL.

That explained why there were 585k keys: given the search volume over the past few days, users were entering all kinds of different queries, and the 3-day accumulation had piled up into 8 GB of vector data.

### Can it be cleaned up? And how?
From a business-logic perspective, this is purely an acceleration cache. Deleting it won’t cause any data inconsistency or business errors—because if the cache is missing, the code will automatically fall back to the LLM and regenerate it.

But **can I just wipe all of it in one shot? No**.
If I deleted all 585k vectors at once while search traffic was still live, every request would suddenly become a Cache Miss. That would send all concurrent search traffic straight to the downstream LLM API, likely triggering rate limits or timeouts on the model service and causing an even bigger secondary incident.

So the best solution was: **reduce memory usage without clearing everything, prioritize deleting the coldest data that hasn’t been accessed for a long time, and keep the hot cache intact.**

## 3. Fine-Grained Cleanup: Precisely Remove the Coldest 50% by Hit Pattern (Idle Time)

So the next question was: how do I determine which vector cache entries in Redis are “cold data” that haven’t been hit in a long time?

The answer was Redis’s native **`OBJECT IDLETIME key`**.
Under `allkeys-lru`, Redis maintains an LRU clock for each key. With `OBJECT IDLETIME`, I can precisely check how many seconds have passed since the key was last read or written (and this query only reads the clock—it does not alter the key’s access time).

I first used a Pipeline to collect the idle-time distribution across all 585k vector keys:

| Idle Time (since last hit) | Key Count | Share | Decision |
| :--- | :--- | :--- | :--- |
| **> 2 days (no access for over 48 hours)** | 149k | 25.59% | 🔴 **Delete candidate (very cold data)** |
| **1 ~ 2 days (no access for 24~48 hours)** | 144k | 24.72% | 🔴 **Delete candidate (cold data)** |
| **12 ~ 24 hours** | 118k | 20.28% | 🟢 **Keep (warm data)** |
| **6 ~ 12 hours** | 69k | 11.82% | 🟢 **Keep (active data)** |
| **1 ~ 6 hours** | 80k | 13.73% | 🟢 **Keep (high-frequency hot data)** |
| **< 1 hour** | 22k | 3.86% | 🟢 **Keep (core hot data)** |

Once the numbers came out, the picture was very clear: **keys with idle time $\ge 24$ hours (queries nobody had searched for in a full day) accounted for exactly 50.3% (294k keys)!**

Those 294k keys were very likely long-tail, low-frequency search queries. Keeping them around brought basically no value other than consuming memory. The remaining 49.7%, on the other hand, had all been hit within the past 24 hours and represented the actually popular queries.

### Execute a Safe Asynchronous Cleanup

To guarantee zero impact on production traffic, I used `SCAN` cursors + batched `Pipeline` checks + **`UNLINK`** (which frees memory asynchronously in a background thread and does not block the main event loop), processing 1000 keys per batch with a 10ms sleep between batches:

```python
import redis
import time

r = redis.Redis(host="your-redis-host", port=6379, socket_timeout=10)

# Threshold: cold data not hit for more than 24 hours
IDLE_THRESHOLD = 86400 

cursor = 0
total_scanned = 0
total_unlinked = 0
batch_to_delete = []

print(f"清理前内存: {r.info('memory').get('used_memory_human')}")

while True:
    cursor, keys = r.scan(cursor=cursor, match="prod:search_emb:*", count=2000)
    if keys:
        pipe = r.pipeline(transaction=False)
        for k in keys:
            pipe.object("idletime", k)
        idles = pipe.execute()

        for k, it in zip(keys, idles):
            total_scanned += 1
            if it is not None and it >= IDLE_THRESHOLD:
                batch_to_delete.append(k)

            # 每凑齐 1000 个调用一次异步 UNLINK
            if len(batch_to_delete) >= 1000:
                r.unlink(*batch_to_delete)
                total_unlinked += len(batch_to_delete)
                batch_to_delete = []
                time.sleep(0.01)  # 短暂停顿，避免主线程抖动

    if cursor == 0:
        break

if batch_to_delete:
    r.unlink(*batch_to_delete)
    total_unlinked += len(batch_to_delete)

time.sleep(2)
print(f"清理完成! 共扫描 {total_scanned} 个，异步清理冷 Key {total_unlinked} 个")
print(f"清理后内存: {r.info('memory').get('used_memory_human')}")
```

### Cleanup Results
The script ran for about 20 seconds:
- It scanned 585,152 keys and precisely deleted **294,350 cold keys (50.30%)**;
- Redis memory dropped immediately from **9.19 GB to 5.22 GB**, freeing up **4.0 GB** of precious space;
- Memory usage fell straight from **99.98% back down to 56.5%**, `Evictions` on the monitoring dashboard dropped to zero, and all alerts affecting Sessions and other core business traffic were fully resolved;
- The downstream LLM API saw no traffic spike at all, and the system got through the incident smoothly.

<img src="https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822000031624.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80" alt="QQ_1787374821275" style="zoom:25%;" />

<center>(Image placeholder: after cleanup, the monitoring dashboard shows memory usage back down to 56% and business traffic returning to a stable state)</center><br>

## 4. Postmortem: What Architectural Problems Did This Expose?

Although the issue was resolved within a little over ten minutes, this memory saturation incident essentially exposed several hard flaws in the earlier architecture design:

### 1. The serialization format was extremely wasteful (string JSON vs binary pack)
When I checked the code, I found that this 1024-dimensional float vector was being written into Redis using `json.dumps(vector)` directly.
A 1024-dimensional float array, once converted into a JSON string, stores every float with a bunch of decimal digits, plus commas and brackets, so each key ended up taking **14.5 KB ~ 21 KB**!

But in reality, 1024 `float32` values packed into binary using Python’s `struct.pack('<1024f', *vector)` only take a fixed **4096 bytes (4 KB)**. Even if I wrapped it in Base64 for compatibility, it would still only be about 5.5 KB.
If binary packing had been used from the start, memory usage for the same number of keys would have dropped by **62%** immediately, and the original 8 GB of data would have gone down to under 3 GB.

### 2. Large acceleration caches and core business data were sharing the same instance (no physical isolation)
This Redis instance was currently being used as a giant “everything bucket”:
it was serving both **large-volume, disposable, recomputable** read-through acceleration caches such as search vectors and presigned URLs, and also **small-volume, low-latency, absolutely must-not-be-lost** core business data such as Sessions, user info, and API rate limiting.

As soon as one acceleration-cache feature gets rolled out or traffic spikes, it can immediately consume the entire instance’s memory and cause core business keys to be evicted by LRU.
This design is obviously unreasonable. Going forward, **high-consumption caches for search/algorithms** must be physically separated from the **core business Redis**.

### 3. The instance size itself was too small
The current primary instance was a `cache.r4.large` (12 GB total physical memory, with only 9.2 GB actually usable by Redis after reserving 25%).
By comparison, Redis instances used by our recommendation system and other compute-heavy services are commonly sized at 64 GB. As search and AI features are being used more and more frequently, a 9.2 GB capacity ceiling is clearly no longer keeping up with business growth. Upgrading the instance size or migrating it is basically inevitable.

## Summary

When troubleshooting incidents in high-risk production components, the rhythm is usually: **use monitoring metrics to quickly classify the problem -> use read-only / low-overhead methods to locate the root cause -> weigh business risk and design the lowest-cost mitigation -> finally close the hole at the code and architecture level**.

This time, cutting by LRU idle time let me quickly push memory usage back into the safe zone while preserving cache hit rate as much as possible. But more importantly, the postmortem helped firmly surface the real issues around serialization compression, physical instance isolation, and capacity planning.