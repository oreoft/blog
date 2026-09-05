---
category: middleware
excerpt: 'Redis memory was full. After clearing out one round of cold data, I only
  got 5 GB back, so I figured I might as well just scale out by adding another shard.


  But only 12 seconds after the slot migration started, `ZADD` in the recommendation
  service began throwing errors like crazy.


  At first I thought the service just hadn’t picked up the new node yet, and that
  a restart would fix it. Turns out even after restarting, the errors were still there.


  Following that `"reachable node:None"` message all the way down, I eventually traced
  it to a line in the `redis-py` client that basically says: “if a node times out,
  remove it from the list.”'
keywords: redis, valkey, elasticache, redis-py, cluster, resharding, moved, 生产事故,
  客户端 bug
lang: en
layout: post
title: Adding Redis Sharding Took Production Writes Down for Over an Hour
---

## Introduction

This started because the Redis instance used by our recommendation system ran out of memory again. `used_memory` hit **79.34G / 79.36G (99.98%)**, and `Evictions` also started climbing, which meant it had already begun throwing data out.

We first tried cleaning things up. The biggest chunk in this DB was exposure history (`device_imp:*` and the like, which records what content each device has seen for recommendation deduplication), taking up more than half the memory, so we started there and deleted keys that hadn't been accessed for over 30 days based on LRU idle time.

The result was pretty underwhelming. The reason was simple: keys untouched for over 30 days mostly belonged to churned users, and those users barely used our product anyway, so their exposure history was tiny to begin with. After all that work, we deleted 880k keys and only freed about 5 GB of memory. Basically a lot of effort for almost nothing.

So my teammate proposed two action items: shorten the TTL, and also just add another shard.

Adding a shard in ElastiCache is an online operation. AWS advertises it as not affecting traffic, and we were also connecting through the cluster-mode configuration endpoint (`clustercfg.xxx`), so in theory the client should automatically detect topology changes.

And that "in theory" was exactly what caused our online exposure writes to break for over an hour. So this post is about what happened at the application layer after adding the shard, and whether cluster move behaved normally. Even if the process is supposed to be transparent, production still deserves respect. Sure enough, things broke right after the scale-out.

## 1. Errors started 12 seconds after the shard was added

First, here's the ElastiCache event timeline (all times are UTC):

```
05:11:29  Scaling out replication group from 1 node groups to 2 node groups
05:15:39  Modified replication group to add 1 new node groups - 0002
05:17:18  Migrating slots from node groups 0001 to 0002 to rebalance slots   ← slot migration starts
05:21:24  Moved a total of 8192 slots out of 8192 slots from shard 0001 to shard 0002
```

The first application-side error appeared at **05:17:30**, exactly 12 seconds after slot migration began.

And during the 12 minutes before that—from the scale-out starting at 05:11 to the new shard being ready at 05:15—not a single error showed up. Adding nodes and creating the shard were both completely fine. It only blew up the moment slots actually started moving.

The error looked like this:

```
ERROR | app.service:215 - info_collect failed,
exception_type=RedisClusterException,
exception=Redis Cluster cannot be connected. Please provide at least one reachable node: None
```

The Datadog graph made it especially obvious: it had been flat at 0, then suddenly shot straight up:

![QQ_1788505007127](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260904015652175.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>The `step.exception` metric had been at 0 the whole time, then jumped straight to 2k–3k / 2min once slot migration started, and stayed there</center><br>

At that rate, it meant 17–25 requests per second were failing to write exposure records.

Quick side note: `info_collect` is one step in our recommendation pipeline. It does three things, and the order matters:

```python
ctx.response.items = rsp_items        # 1. First assemble the recommendation results to return to the user
self.stats(ctx)                       # 2. Emit metrics
await PosterMgr.run_all(ctx, ...)     # 3. Finally write exposure records to Redis  ← this is where it blew up
```

The response is already assembled in step 1, so step 3 failing doesn't affect the user getting recommendations. So throughout this entire incident, **the API kept returning 200s, with no timeouts, no 5xxs, and no user complaints at all**. It was completely silent. If I hadn't happened to be looking at this Redis key distribution at the time, it probably would have stayed broken even longer.

## 2. I thought a restart would fix it. It didn't.

Seeing "cannot be connected", my first reaction was very natural: when the service started, there was only one shard. Now there were two, and maybe it didn't know that. The old process was holding stale topology info, so restarting it to fetch topology again should fix it, right?

So I restarted it.

**After the restart, it was still failing.**

That made things more interesting. And even more confusing: the startup logs clearly showed initialization succeeding:

```
06:01:41 | app.core.database_manager:299 - Redis Cluster connection initialized -
          host=clustercfg.xxx-redis.xxx.cache.amazonaws.com, port=6379,
          max_connections=300, use_tls=True
```

There wasn't a single `initialization failed` log. In other words, **the process connected just fine at startup, then somehow broke while running**.

Later I compared timestamps: initialization succeeded at 06:02, and errors started again at 06:09. So it relapsed after about 7 minutes. Restarting only bought us a few more minutes of life.

At that point, the hypothesis that "the service didn't detect the new node" no longer held up. The new process clearly did detect it. It just forgot again after running for a while.

## 3. The `None` at the end of the error was the real clue

Later I pulled the full traceback, and only then noticed an important detail:

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

At first I thought this error message wasn't very informative. "Please provide at least one reachable node" sounded like a plain network issue. But the network was clearly fine—I could connect to the cluster manually from the bastion host with no problem.

The key was that final `None`. I checked the redis-py source, and this is how that exception gets built:

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

If this were really a connectivity issue, `exception` should have contained a `ConnectionError` or `TimeoutError`. But it was `None`, which means the `for` loop never ran even once—in other words, `self.startup_nodes` was empty.

**It wasn't that the client couldn't connect to any node. It was that the client no longer had any nodes left to connect to.**

## 4. How the client lost all its nodes

Following that lead, I kept digging through redis-py and found this in the exception handling inside `execute_command` (we were using `redis==5.0.0` in production):

```python
except (ConnectionError, TimeoutError):
    # Connection retries are being handled in the node's Retry object.
    # Remove the failed node from the startup nodes before we try
    # to reinitialize the cluster
    self.nodes_manager.startup_nodes.pop(target_node.name, None)   # ← this is the line
    await self.close()
    raise
```

As soon as a node times out, it gets removed from `startup_nodes`. The design assumption here is: "there are still other nodes available for rediscovering topology."

But there was a second trap too. I verified this on the bastion host:

```
When constructing the client: startup_nodes = [clustercfg.xxx...]
After first initialization:   startup_nodes = [0001-001, 0002-001]   ← replaced by discovered real nodes
```

**The `clustercfg` configuration endpoint you provide gets discarded after the first successful initialization**, and replaced with the concrete nodes discovered at that time.

Those two traps together were what made this fatal:

```
Before scale-out: single shard → after first initialization, the list only contains {0001-001}
                               (the clustercfg endpoint has already been overwritten and lost)
    ↓
05:17:18 slot migration starts, connection jitter happens, ConnectionError/TimeoutError is raised
    ↓
startup_nodes.pop("0001-001")   → the list becomes empty
    ↓
await self.close()              → marks the client as needing reinitialization
    ↓
Every command afterward → initialize() → iterates over an empty list → exception stays None
                       → raise "...reachable node: None"
    ↓
Permanently wedged; it never recovers unless the process restarts
```

So this is especially easy to hit when scaling from a single shard, because the list only has one node. One `pop`, and it's empty. If the cluster had already had multiple shards, deleting one node would still leave others, and it probably could have recovered on its own. We just happened to be in the worst possible scenario.

One thing that confused me at the time was that there were no timeout errors anywhere in the logs. Later it made sense: that `ConnectionError` was swallowed inside redis-py's internal retry loop. After the `pop`, it does `raise`, the outer retry logic catches it and calls `initialize()` again, and this time it hits the empty node list, so what finally bubbles up is `RedisClusterException`. That's all the application sees. **No timeout in the logs does not mean no timeout actually happened.**

## 5. This isn't new—people had already hit it on GitHub

I searched around and found an issue in the redis-py repo describing exactly the same problem:

> **[RedisCluster becomes unrecoverable if all nodes timeout · Issue #3221](https://github.com/redis/redis-py/issues/3221)**

The title was literally our symptom. It explicitly points to that `startup_nodes.pop` line as the root cause, and also mentions that it's especially bad in single-node cluster setups, which matched our case perfectly.

There was another related issue too:

> **[async redis cluster should use initial startup nodes during reinitialization in case of failover · Issue #2472](https://github.com/redis/redis-py/issues/2472)**

This one describes the second trap: the async version overwrites the startup nodes you originally configured during first initialization.

Put those two issues together, and you get the full picture of our incident. The frustrating part is that **#3221 is marked `closed as not planned` + `stale`**. Upstream basically didn't care and let it auto-close.

## 6. Why another service was unaffected: the version was three major releases newer

There was one thing during the investigation that kept bothering me: another backend service of ours was connected to the same cluster, went through the exact same scale-out, and had zero issues.

At first I thought it was due to different initialization styles:

```python
# The other service: pass host/port directly
RedisCluster(host=host, port=port, ssl=..., decode_responses=True, ...)

# Recommendation service: pass startup_nodes
startup_nodes = [ClusterNode(host=host, port=port)]
RedisCluster(startup_nodes=startup_nodes, ssl=..., ...)
```

I ran a comparison test using the same redis-py version, and it turned out both styles behaved exactly the same: both got overwritten, both could get stuck. Inside redis-py, `host=`/`port=` just gets converted into a `ClusterNode` and stuffed into `startup_nodes` anyway, so they end up on the same code path.

That left only one variable: the version.

```
Other service         : redis[hiredis]~=8.0.0      → uv.lock pins 8.0.0
Recommendation service: redis==5.0.0               → confirmed by the traceback path
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

The list never becomes empty, so `reachable node: None` can never happen.

Same cluster, same slot migration, same scale-out, two services: one got wedged, one didn't. The only variable was the client version. Honestly, the variable control was cleaner than most lab experiments.

A quick side note on something that's easy to mix up: **the client version number does not map 1:1 to the server engine version**. The `8` in redis-py 8.x has no direct relationship to the `8` in Valkey 8.2. They don't need to match, and things still work fine. Our server was Valkey 8.2.0 (`INFO` still reports `redis_version` as 7.2.4, because Valkey intentionally pretends to be old Redis for compatibility), while our clients were 5.0.0 and 8.0.0, and both could connect and read/write normally.

But "it works" doesn't mean "it's fine to leave it like that forever." **If the server engine version moves forward, the client should ideally move forward too, and not lag too far behind.** I think that's the real takeaway here. There are two reasons:

First, new engine features are simply unavailable to old clients. RESP3 support, newer commands, client-side caching—those all require client support too. Upgrading only the server is basically wasting the upgrade.

Second, old clients accumulate bugs that were fixed long ago, but you still haven't benefited from those fixes. **This incident was exactly that second category.** Version 5.0.0 was from August 2023, and we missed every fix across three major releases, including the removal of that `pop` line.

So the reason to upgrade needs to be framed correctly: it's not "the client version must match the server version," it's "the client shouldn't stay frozen forever." That distinction matters. Otherwise next time someone might draw a ridiculous conclusion like "then should we downgrade the server instead?" (No. The bug is in the client. It has nothing to do with the server version.)

## 7. Temporary mitigation: add a watchdog

At the time, we understood the root cause, but upgrading a client library across three major versions in the middle of the night felt too risky, so we first added a watchdog as a safety net.

The idea was simple: if the client can get itself into a permanently unrecoverable state, then something outside it should monitor it and rebuild it when that happens:

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
            # Only RedisClusterException means the client entered a non-self-healing state;
            # transient errors like timeouts can recover on their own, and rebuilding would just add noise
            continue
        # rebuild using the original configuration endpoint
        new_client = await self._build_client()
        old_client, self.client = self.client, new_client
        await old_client.close()
```

There were two details I paid special attention to:

1. Rebuilding must use the original configuration endpoint (`clustercfg`), not whatever nodes the client currently has in memory, because its current node list is already corrupted.
2. Only rebuild on `RedisClusterException`. My first instinct was "rebuild on any error," but that would be bad—if the network hiccups, rebuilding can easily create a rebuild storm, and in those cases the client can recover by itself anyway.

We set the detection interval to 10 seconds, which means in the worst case we'd lose 10 seconds of exposure data. Compared to "permanently wedged until someone manually restarts it," that was acceptable.

During the day, we also cleaned things up on the Redis side and ran verification. Only then was the issue truly under control. The before/after comparison was very clear (20-second window):

| | During incident | After recovery |
|---|---:|---:|
| MOVED on shard 0001 | +5,567 | +1 |
| ZADD rejected on shard 0001 | +5,560 | +0 |
| ZADD succeeded on shard 0002 | +0 | +5,656 |
| Total commands on shard 0002 | +28 | +16,902 |

The new shard finally started receiving traffic, and writes were now being split normally across the two halves of the slot range.

<img src="https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260904015735296.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80" alt="QQ_1788505052649" style="zoom:33%;" />

<center>After the watchdog was deployed, `step.exception` dropped back to a normal level</center><br>

There was also a small side story here. The curve dropped, but not all the way to zero—it was still around 14%. After checking, we found one old-version instance hadn't been replaced. Out of 7 instances, 1 was still old, and 1/7 = 14.3%, which matched the residual error ratio exactly. Once we stopped that instance, everything was clean.

## 8. Postmortem: a few things more worth remembering than the bug itself

**1. The most troublesome failures aren't the ones that error—they're the ones that don't**

Throughout this incident, the API kept returning 200s. No timeouts, no 5xxs, no user complaints. Exposure writes were silently lost for over an hour, and luckily I happened to notice.

The root cause was this code:

```python
try:
    await step_ins.do_process(ctx)
except Exception as e:
    logger.error("{} failed, ...", step_name, ...)
    datadog_agent.increment("step.exception", tags=["step:" + step_name])
    continue      # ← swallow it and continue to the next step
```

This `except + continue` pattern isn't wrong by itself. If exposure writing fails, it really shouldn't take down the whole recommendation API. **The problem is that this degradation path had no alerting attached to it.** The metric had been emitted the whole time, but nobody had set a threshold on it. A failure that could swallow one-third of all writes just sat there in metrics for over an hour with nobody looking. That's the real hole we need to patch.

**2. "Try restarting it" can be misleading**

After the restart, the error count did go down for a while, which makes it very easy to think, "looks fixed, let's keep watching." In reality, the new process just started from a clean state and then fell into the exact same trap 7 minutes later. To tell whether something is really fixed, you can't just look at whether errors dropped—you need to look at how far they dropped, whether they hit zero, and whether they bounce back.

**3. When a cloud vendor says "online scale-out doesn't affect traffic," they mean the server side**

And to be fair, the server side really did its job. Throughout the whole process, `cluster_state: ok`, all 16384 slots remained assigned, and no data was lost. **But whether the client can keep up with topology changes is a separate matter, and that's your responsibility.**

Next time we do this kind of topology change, the runbook should include one extra step: after the change, check `INFO commandstats` on every shard and confirm the new shard is actually receiving business traffic. This time, the new shard held half the slots and 4.33 million keys, yet its business command count was 0. That signal was already pretty obvious—we just didn't think to look until after the fact.

## Summary

My biggest takeaway from this incident is that every link in the failure chain looked "reasonable" when viewed in isolation.

The cloud vendor's online scale-out worked fine; the server stayed healthy the whole time. We used a cluster client and connected through the configuration endpoint, which was also correct. Exceptions were caught and degraded gracefully, preventing the whole API from going down, which even sounds like a good practice. And yet all of those individually reasonable pieces, combined with one line in the client library that says "remove the node if it times out," turned into a completely silent production incident that lasted over an hour.

Another takeaway was about debugging method. Along the way I disproved four of my own hypotheses: "stale topology caused retries to exhaust," "redis 5.0.0 is fundamentally broken for cluster," "reinitialization clears the node list," and "close clears the node list." Every one of them sounded plausible at the time, and every one was disproven by experiments. In the end, the thing that really nailed the problem was that lonely little `None` at the end of the error message.

But after going in such a big circle, the final conclusion was actually pretty simple: **this was a version problem**. That `pop` line in 5.0.0 is a real bug. It's already gone in 8.0.0. Same cluster, same scale-out, and the service running 8.0.0 was unaffected.

So the most practical lesson is still the same one from earlier: **if the server engine version moves forward, don't let the client lag too far behind**. Missing out on new features is one thing. What's really dangerous is missing fixes you should have gotten for free just by upgrading. Most of the time you won't notice the difference when everything is calm. But once you do topology changes like scale-out, scale-in, or failover, that technical debt gets collected all at once. We let ours sit untouched across three major versions, and this time we paid the interest too.