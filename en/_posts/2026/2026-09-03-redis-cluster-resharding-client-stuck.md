---
category: middleware
excerpt: Redis memory was full. After one round of clearing cold data, usage only
  dropped by 5 GB, so I decided to just add a shard and scale out directly. As a result,
  only 12 seconds after slot migration started, `ZADD` in the recommendation service
  began throwing errors like crazy. I thought the service just hadn’t picked up the
  new node and a restart would fix it, but it was still failing even after the restart.
  Following that `"reachable node:None"` message all the way down, I eventually traced
  it to a line in the `redis-py` client that basically says, “if a node times out,
  remove it from the list.”
keywords: redis, valkey, elasticache, redis-py, cluster, resharding, moved, 生产事故,
  客户端 bug
lang: en
layout: post
title: Adding a Redis Shard Took Down Production Writes for Over an Hour
---

## Introduction

This started because the Redis instance used by our recommendation system ran out of memory again. `used_memory` was pinned at **79.34G / 79.36G (99.98%)**, and `Evictions` had started climbing too, which meant it was already throwing data out.

I first tried cleaning things up. The biggest chunk in this DB was exposure history (`device_imp:*`-style keys, which record what content each device has seen so recommendations can dedupe against it), and it was taking more than half the memory, so I went after that first: deleting keys that hadn't been accessed for over 30 days based on LRU idle time.

The result was pretty underwhelming. The reason was simple: anything not accessed for 30+ days was basically from churned users, and those users barely use our product anyway, so their exposure histories were tiny to begin with. After all that work, I deleted 880k keys and memory only dropped by 5 GB. Basically a lot of effort for almost nothing.

So my teammate proposed two action items: shorten the TTL, and also add a shard directly.

Adding a shard in ElastiCache is an online operation. AWS advertises it as having no business impact, and we were also connecting through the cluster-mode configuration endpoint (`clustercfg.xxx`), so in theory the client should automatically detect topology changes.

And it was exactly that "in theory" that caused our online exposure writes to break for over an hour. So after adding the shard, I checked what was happening at the application layer and whether cluster move was working properly. Even if it's supposed to be transparent, production deserves respect. Sure enough, things broke right after the scale-out.

## 1. Errors started 12 seconds after adding the shard

First, here's the ElastiCache event timeline (all times are UTC):

```
05:11:29  Scaling out replication group from 1 node groups to 2 node groups
05:15:39  Modified replication group to add 1 new node groups - 0002
05:17:18  Migrating slots from node groups 0001 to 0002 to rebalance slots   ← slot migration starts
05:21:24  Moved a total of 8192 slots out of 8192 slots from shard 0001 to shard 0002
```

The first application-side error appeared at **05:17:30**, exactly 12 seconds after slot migration began.

And during the 12 minutes before that—from the scale-out starting at 05:11 to the new shard being created at 05:15—not a single error showed up. Adding nodes was fine, creating the shard was fine, but the moment slots actually started moving, everything blew up.

The error looked like this:

```
ERROR | app.service:215 - info_collect failed,
exception_type=RedisClusterException,
exception=Redis Cluster cannot be connected. Please provide at least one reachable node: None
```

The Datadog graph was super intuitive: it had been flat at 0, then suddenly shot straight up:

![QQ_1788505007127](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260904015652175.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>The `step.exception` metric had been 0 the whole time. Once slot migration started, it jumped straight to 2k–3k / 2min and stayed there</center><br>

At that rate, it meant 17–25 requests per second were failing to write exposure records.

Quick side note: `info_collect` is a step in our recommendation pipeline. It does three things, and the order matters:

```python
ctx.response.items = rsp_items        # 1. First assemble the recommendation results to return to the user
self.stats(ctx)                       # 2. Emit metrics
await PosterMgr.run_all(ctx, ...)     # 3. Finally write exposure records to Redis  ← this is where it blew up
```

The response is already assembled in step 1, so step 3 blowing up doesn't affect the user getting recommendations. So throughout this whole incident, **the API returned 200 the entire time—no timeouts, no 5xx, no user complaints at all**. It was completely silent. If I hadn't happened to be looking at this Redis key distribution at the time, it probably would have stayed broken even longer.

## 2. I thought a restart would fix it. It didn't.

Seeing "cannot be connected", my first reaction was very natural: when the service started, there was only one shard; now there's a second one, so maybe it doesn't know about it. The old process was holding stale topology info, so restarting it to fetch topology again should fix it, right?

So I restarted it.

**After the restart, it was still erroring.**

That made things interesting. Even more confusing: the startup logs clearly showed initialization succeeding:

```
06:01:41 | app.core.database_manager:299 - Redis Cluster connection initialized -
          host=clustercfg.xxx-redis.xxx.cache.amazonaws.com, port=6379,
          max_connections=300, use_tls=True
```

There wasn't a single `initialization failed`. In other words, **the process connected just fine at startup, then broke by itself while running**.

Later I matched the timestamps: initialization succeeded at 06:02, and errors started again at 06:09. So it relapsed after about 7 minutes. Restarting only bought us a few more minutes of life.

At that point, the hypothesis that "the service didn't detect the new node" no longer held. The new process clearly *did* detect it—it just forgot again after running for a while.

## 3. That final `None` in the error was the real clue

Later I pulled the full traceback, and only then noticed a detail:

```
File "/usr/local/lib/python3.11/site-packages/redis/asyncio/cluster.py", line 685, in execute_command
    await self.initialize()
File "/usr/local/lib/python3.11/site-packages/redis/asyncio/cluster.py", line 392, in initialize
    await self.nodes_manager.initialize()
File "/usr/local/lib/python3.11/site-packages/redis/asyncio/cluster.py", line 1300, in initialize
    raise RedisClusterException(
redis.exceptions.RedisClusterException: Redis Cluster cannot be connected.
Please provide at least one reachable node: None
```

<img src="https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260904020221262.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80" alt="QQ_1788505311066" style="zoom:25%;" />

At first I thought this error message was useless. "Please provide at least one reachable node"—isn't that just saying the network is down? But the network was clearly fine. I could connect to the cluster manually from the bastion host without any issue.

The key was that final `None`. Looking at redis-py's source, the exception is built like this:

```python
exception = None
for startup_node in self.startup_nodes.values():
    try:
        cluster_slots = await startup_node.execute_command("CLUSTER SLOTS")
        startup_nodes_reachable = True
    except Exception as e:
        exception = e          # ← if connection fails, the error is stored here
        continue

if not startup_nodes_reachable:
    raise RedisClusterException(
        f"...Please provide at least one reachable node: {str(exception)}"
    )
```

If it were truly a connectivity issue, `exception` should contain a `ConnectionError` or `TimeoutError`. But it was `None`, which means this `for` loop never ran even once—in other words, `self.startup_nodes` was empty.

**It wasn't that it couldn't connect to any node. The client no longer had any nodes left to connect to.**

## 4. How the client lost all its nodes

Following that lead, I dug further into redis-py's code and found this in the exception handling inside `execute_command` (we were using `redis==5.0.0` in production):

```python
except (ConnectionError, TimeoutError):
    # Connection retries are being handled in the node's Retry object.
    # Remove the failed node from the startup nodes before we try
    # to reinitialize the cluster
    self.nodes_manager.startup_nodes.pop(target_node.name, None)   # ← this line right here
    await self.close()
    raise
```

If a node times out, it gets removed from `startup_nodes`. The design assumption here is: "there are still other nodes available for rediscovering topology."

But there was a second trap too. I verified this on the bastion host:

```
When constructing the client:   startup_nodes = [clustercfg.xxx...]
After first initialization:     startup_nodes = [0001-001, 0002-001]   ← overwritten by discovered real nodes
```

**The `clustercfg` configuration endpoint you provide gets discarded after the first successful initialization**, replaced by the concrete nodes discovered at that moment.

Those two traps together were fatal:

```
Before scale-out: single shard → after first initialization, the list contains only {0001-001}
                                 (the clustercfg endpoint has already been overwritten and lost)
    ↓
05:17:18 slot migration starts, connection jitter occurs, ConnectionError/TimeoutError is raised
    ↓
startup_nodes.pop("0001-001")   → the list becomes empty
    ↓
await self.close()              → marks the client as needing reinitialization
    ↓
Every subsequent command → initialize() → iterate over an empty list → exception stays None
                         → raise "...reachable node: None"
    ↓
Permanently wedged; it never recovers unless the process is restarted
```

So scaling out from a single shard is especially easy to break, because the list only has one node. Pop it once and you're done. If this had already been a multi-shard cluster, removing one node would still leave others, and it probably could have crawled back on its own. We just happened to hit the worst-case scenario.

One more thing confused me at the time: there were no timeout errors anywhere in the logs from start to finish. Later I realized why. That `ConnectionError` was swallowed inside redis-py's internal retry loop. After the pop, it does `raise`, the outer retry logic catches it, then calls `initialize()` again. This time it hits the empty node list, and what bubbles up is `RedisClusterException`. So the application layer only sees the final exception. **No timeout in the logs does not mean no timeout ever happened.**

## 5. This isn't new—people already hit it on GitHub

I searched around and found an issue in the redis-py repo describing exactly the same thing:

> **[RedisCluster becomes unrecoverable if all nodes timeout · Issue #3221](https://github.com/redis/redis-py/issues/3221)**

The title was literally our symptom. It explicitly points to that `startup_nodes.pop` line as the root cause, and also mentions that it's especially severe in single-node cluster setups—which matches our case perfectly.

There was another related issue too:

> **[async redis cluster should use initial startup nodes during reinitialization in case of failover · Issue #2472](https://github.com/redis/redis-py/issues/2472)**

This one describes the second trap: the async version overwrites the startup nodes you originally configured during first initialization.

Put those two issues together, and you basically get the full puzzle of our incident. The frustrating part is that **#3221 is marked `closed as not planned` + `stale`**. Upstream didn't really care about it and let it get auto-closed.

## 6. Why another service was totally fine: the version differed by three major releases

During the investigation, one thing really didn't make sense at first: another backend service of ours was connected to the same cluster, went through the exact same scale-out, and had absolutely no issue.

At first I thought it was due to different usage patterns:

```python
# The other service: pass host/port directly
RedisCluster(host=host, port=port, ssl=..., decode_responses=True, ...)

# Recommendation service: pass startup_nodes
startup_nodes = [ClusterNode(host=host, port=port)]
RedisCluster(startup_nodes=startup_nodes, ssl=..., ...)
```

I ran a controlled experiment using the same redis-py version, and both styles behaved exactly the same: both got overwritten, both could wedge permanently. Internally, `host=`/`port=` just gets turned into a `ClusterNode` and stuffed into `startup_nodes`, so both paths converge.

That left only one variable: the version.

```
Other service      : redis[hiredis]~=8.0.0      → uv.lock pinned to 8.0.0
Recommendation svc : redis==5.0.0               → confirmed by the traceback path
```

That's a full three major versions apart. I checked the same code path in 8.0.0, and that `pop` line is gone:

```python
# 5.0.0 —— directly removes the node from the list
self.nodes_manager.startup_nodes.pop(target_node.name, None)

# 8.0.0 —— no longer removes it; just moves the failed node to the end and retries later
target_node.update_active_connections_for_reconnect()
await target_node.disconnect_free_connections()
self.nodes_manager.move_node_to_end_of_cached_nodes(target_node.name)
e.last_failed_node_name = target_node.name
```

The list never becomes empty, so `reachable node: None` never happens.

Same cluster, same slot migration, two services: one wedged, one fine. The only variable was the client version. Honestly, that's cleaner than most lab experiments.

A quick side note on something that's easy to mix up: **the client version number and the server engine version number are not directly tied**. The `8` in redis-py 8.x has no direct relationship to the `8` in Valkey 8.2. They don't need to match for things to work. Our server was Valkey 8.2.0 (`INFO` still reports `redis_version` as 7.2.4, because Valkey intentionally pretends to be old Redis for compatibility), and both a 5.0.0 client and an 8.0.0 client could connect and read/write just fine.

But "it works" doesn't mean it's okay to leave it that way forever. **If the server engine keeps moving forward, the client should generally move forward too—don't let it lag too far behind.** I think that's the real takeaway here. Two reasons:

First, new engine features are simply unavailable to old clients. RESP3, new commands, client-side caching—if the client doesn't support them, upgrading the server alone is basically wasted.

Second, old clients accumulate bugs that were fixed long ago, but you still haven't benefited from those fixes. **This incident was exactly that second case.** Version 5.0.0 was from August 2023. We missed every fix across three major releases, including the removal of that `pop`.

So the reason to upgrade needs to be framed correctly: it's not "the client version must match the server version", it's "the client can't stay frozen forever." That distinction matters, otherwise next time someone might draw some wild conclusion like "then should we downgrade the server?" (No. The bug is in the client. The server version has nothing to do with it.)

## 7. Temporary mitigation: add a watchdog

At the time, we understood the root cause, but upgrading a client library across three major versions in the middle of the night felt too risky. So we first added a watchdog as a safety net.

The idea was simple: if the client can get itself into a permanently unrecoverable state, then something outside it should watch for that and throw it away when it happens:

```python
async def _watchdog(self):
    while True:
        await asyncio.sleep(self.WATCHDOG_INTERVAL_SECONDS)   # 10 seconds
        ping_task = asyncio.ensure_future(self.client.ping())
        done, _ = await asyncio.wait({ping_task}, timeout=self.WATCHDOG_PING_TIMEOUT_SECONDS)
        if ping_task not in done:
            ping_task.cancel()      # treat slow ping as a transient issue; don't rebuild
            continue
        error = ping_task.exception()
        if error is None or not isinstance(error, RedisClusterException):
            # Only RedisClusterException means the client is in a non-self-healing state;
            # transient errors like timeouts can recover on their own, and rebuilding would just add noise
            continue
        # Rebuild using the original configuration endpoint
        new_client = await self._build_client()
        old_client, self.client = self.client, new_client
        await old_client.close()
```

There were two things I paid special attention to:

1. Rebuilding must use the original configuration endpoint (`clustercfg`), not whatever nodes the client currently holds, because that internal list is already corrupted.
2. Only rebuild on `RedisClusterException`. My first instinct was "rebuild on any error", but that would be bad—if the network jitters, you'd trigger rebuild storms, and those transient cases can recover on their own anyway.

The detection interval was set to 10 seconds, which means in the worst case we'd lose 10 seconds of exposure writes. Compared to "permanently wedged until someone manually restarts it", that was acceptable.

Later during the day we also cleaned things up on the Redis side and ran verification. Only then was the issue truly under control. The before/after numbers were very clear (20-second window):

| | During incident | After recovery |
|---|---:|---:|
| MOVED on shard 0001 | +5,567 | +1 |
| ZADD rejected on shard 0001 | +5,560 | +0 |
| ZADD succeeded on shard 0002 | +0 | +5,656 |
| Total commands on shard 0002 | +28 | +16,902 |

The new shard finally started receiving traffic, and writes were correctly split in half by slot ownership.

<img src="https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260904015735296.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80" alt="QQ_1788505052649" style="zoom:33%;" />

<center>After the watchdog went live, `step.exception` dropped back to a normal level</center><br>

There was also a small side story here. The graph came down, but not to zero—it was still around 14%. After checking, I found one old-version instance that hadn't been replaced. Out of 7 instances, 1 was still old, and 1/7 = 14.3%, which matched the residual error ratio perfectly. Once we stopped that instance, everything was clean.

## 8. Postmortem: a few things more worth remembering than the bug itself

**1. The most annoying failures aren't the ones that error—they're the ones that don't**

Throughout this incident, the API returned 200 the whole time. No timeouts, no 5xx, no user complaints. Exposure writes were silently lost for over an hour, and luckily I happened to notice.

The root cause is in this code:

```python
try:
    await step_ins.do_process(ctx)
except Exception as e:
    logger.error("{} failed, ...", step_name, ...)
    datadog_agent.increment("step.exception", tags=["step:" + step_name])
    continue      # ← swallow it and continue to the next step
```

This `except + continue` pattern isn't wrong by itself. If exposure writing fails, it really shouldn't bring down the whole recommendation API. **The problem is that this degradation path had no alerting attached.** The metric was being emitted the whole time; nobody had set a threshold on it. A failure that can silently drop a third of your writes sat there for over an hour with no one noticing. That's the real hole we need to patch.

**2. "Try restarting it" can absolutely mislead you**

After the restart, the error count did go down for a while, which makes it very easy to think, "Looks fixed, let's keep watching." In reality, the new process just started from a clean state and fell into the exact same hole 7 minutes later. To judge whether something is truly fixed, you can't just look at whether the error count dropped—you need to see *how far* it dropped, whether it hit zero, and whether it rebounds.

**3. When cloud vendors say "online scale-out doesn't affect business", they're talking about the server side**

And to be fair, the server side really did its job. Throughout the whole process, `cluster_state: ok`, all 16384 slots were assigned the whole time, and not a single piece of data was lost. **But whether the client can keep up with topology changes is a separate matter. That's your responsibility.**

Next time we do this kind of topology change, the runbook should include one more step: after the change, check `INFO commandstats` on every shard and confirm the new shard is actually receiving business traffic. In this incident, the new shard owned half the slots and 4.33 million keys, yet its business command count was 0. That signal was already pretty obvious—we just only thought to look at it afterward.

## Summary

My biggest takeaway from this incident is that every link in the failure chain looked pretty "reasonable" on its own.

The cloud vendor's online scale-out worked fine; the server stayed healthy the whole time. We used a cluster client, connected to the configuration endpoint, and the usage pattern was correct. Exceptions were caught and degraded gracefully so the whole API wouldn't fail—which even sounds like a good practice. But when you stack a bunch of individually reasonable things together, plus one line in the client library that says "if a node times out, remove it", you end up with a completely silent production incident lasting over an hour.

Another takeaway was about debugging method. Along the way I disproved four of my own hypotheses: "stale topology caused retries to exhaust", "redis 5.0.0 is just fundamentally broken with clusters", "reinitialization clears the node list", and "close clears the node list". Every one of them sounded plausible at the time, and every one got disproven by experiments. In the end, the thing that really nailed the issue was that lonely little `None` at the end of the error message.

But after going in such a big circle, the final conclusion was actually pretty simple: **this was a version problem**. That `pop` line in 5.0.0 was a real bug. It's already gone in 8.0.0. Same cluster, same scale-out, and the service running 8.0.0 had no issue at all.

So the most practical lesson is still the same one from earlier: **if the server engine keeps moving forward, don't let the client fall too far behind**. Missing out on new features is one thing; what's really dangerous is missing fixes you should have gotten for free. Most of the time you won't notice the difference. But once you do topology changes like scale-out, scale-in, or failover, that technical debt gets collected all at once. We let ours sit untouched across three major versions, and this time we paid the interest too.