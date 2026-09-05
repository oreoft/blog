---
category: middleware
excerpt: 'In the previous post, I got the hang issue after upgrading `redis-py` to
  8.x under control, but there was still one error curve left on the cluster: 42%
  of read commands were being redirected by `MOVED`, connections didn’t survive for
  more than 1 second, and user profiles were getting lost without the business side
  noticing anything. I suspected socket timeouts, topology rebuilds, and the client’s
  internal state one after another. Every one of them could reproduce similar symptoms
  on the bastion host, but none of them matched the evidence from production. In the
  end, what pinned the issue down was a single `INFO` line in the container startup
  logs.'
keywords: redis, valkey, elasticache, redis-py, cluster, moved, address_remap, dotenv,
  生产事故, 排查
lang: en
layout: post
title: 'After Upgrading the Client, Redis Started Returning Tons of MOVED Errors Again:
  A Local Config That Had Been Lurking for Seven Months'
---

## Introduction

At the end of the previous post ([We added a shard to Redis and broke production writes for over an hour](/middleware/2026/09/03/redis-cluster-resharding-client-stuck.html)), upgrading redis-py from 5.0.0 to 8.x stopped the client hang issue.

What it stopped was only the hanging.

The next day, when I looked at that cluster again, `INFO errorstats` was sitting on tens of millions of `MOVED` responses, and the rejection rate for read commands was hovering around 40%:

```
zrevrange         42.5% MOVED
zrangebyscore     35.6%
hgetall           44.9%
```

In CloudWatch, each shard was creating 440 new connections per second, but only 280 were connected at any given time. In other words, each connection lived for about half a second on average before being dropped and recreated.

There was business impact too. In the recommendation service, one provider is responsible for reading users' like, play, and favorite history. If the Redis read fails, the whole provider throws an exception. An outer `except Exception` catches it, logs one critical line, and then continues. The API still returns 200 as usual. So the user profile data was silently dropped, and the request itself showed no obvious error. Worse, that critical log line never made it into Datadog, so this incident left almost no visible trace.

<center>(Image placeholder: Redis error curve in Datadog, or CloudWatch NewConnections curve staying high)</center><br>

This post records the next day and a half of investigation. The final cause wasn't complicated, but I think the way those intermediate hypotheses were proposed and then ruled out is more useful than the conclusion itself.

## 1. First, figure out which machines are connecting

This time I didn't start by guessing the cause. I started by figuring out **who was connecting to this cluster**.

`CLIENT LIST` showed 21 client IPs. I mapped them back through ECS, and got this:

| Service | Machine Count | redis-py | Connection Lifetime |
|---|---|---|---|
| **Recommendation service** | 8 | **8.1.0** | **1–3 seconds** |
| API service | 8 | 8.0.0 | 1.8–5 hours |
| Event consumer service | 1 | 7.1.0 | 68 minutes |

All 8 recommendation service machines were constantly rebuilding connections. Right next to it, another backend API service (I'll call it the API service below) was connecting to the same cluster, also using redis-py 8.x, and its connections lived for hours. Same cluster, same major library version, but one was on a seconds scale and the other on an hours scale. From this point on, the API service became the best control group.

Then I looked at error attribution. The server-side `errorstats` is a global counter and doesn't distinguish clients, but the three services happened to use completely non-overlapping command sets: the recommendation service used `zrevrange` and `zrangebyscore`, the API service only used `zrevrangebyscore`, and the event consumer service only used `zremrangebyscore`. Matching that against the rejection rates:

```
zrevrange          42.5% MOVED   ← exclusive to recommendation service
zrangebyscore      35.6%         ← exclusive to recommendation service
zrevrangebyscore    0.004%       ← exclusive to API service
zremrangebyscore    0.0%         ← exclusive to event consumer service
```

Same cluster, same moment in time: commands used only by the recommendation service were getting 40% MOVED, while the other two services were at 0. **All MOVEDs were coming from the recommendation service.**

The problem was now compressed into one sentence: **same library, same cluster — why does the recommendation service break while the API service doesn't?**

## 2. Hypothesis 1: the removed `socket_timeout`

The first thing that came to mind was socket timeout. There were two reasons.

First, the only client config difference between the recommendation service and the API service was exactly this: the API service had `socket_timeout=3, socket_connect_timeout=2`, while the recommendation service had removed those two parameters the day before. Second, the deleted comment was very explicit:

```python
-  # Bounded connect/read/write: a hung socket times out and closes itself,
-  #   instead of exposing a blocked await to external cancellation
-  #   (which is exactly the window where pool slot leaks happen)
```

Without timeouts, a blocked await can only end through external cancellation, and cancellation is exactly the window where connection pool leaks can happen. It looked like a complete causal chain.

But when I checked it against reality, two things didn't line up. First, timeout is a fallback mechanism. The service itself had no visible errors, and a healthy service should not have 440 hung sockets per second. **Missing a fallback doesn't create a failure; it just fails to catch one once it happens.** Second, if this were really a leak, the number of live connections should keep climbing until it hit the limit of 300 and then start erroring. But it stayed stable at 280. **Stable live connections plus hundreds of new connections per second means the connection objects themselves are not leaking — it's the same set of objects whose sockets are repeatedly disconnecting and reconnecting.**

So this hypothesis was ruled out.

## 3. Hypothesis 2: MOVED and connection rebuilds are triggering each other

The second idea came from reading the library source. redis-py handles MOVED like this:

```python
except MovedError as e:
    self.reinitialize_counter += 1
    if self.reinitialize_counter % self.reinitialize_steps == 0:   # default 5
        await self.aclose()       # close the whole client
    else:
        await self.nodes_manager.move_slot(e)   # only fix this one slot
```

Every 5 MOVEDs, the client decides its topology is stale, closes and rebuilds the entire client, and invalidates all connections. And during each rebuild, `set_nodes()` marks all connections on all nodes as needing reconnect — the library author's comment says it very directly: "reconnect is lazy and cheap", assuming topology changes are rare.

So I got a chain that looked self-consistent: MOVED triggers rebuild, rebuild invalidates all connections, routing changes during rebuild, commands go to the wrong node, which creates more MOVEDs. The numbers even lined up: 208 MOVEDs per second, divided by 5, is about 41 rebuilds; measured `CLUSTER SLOTS` was about 30 times per second, same order of magnitude.

But one part of this chain didn't make sense. If the connection is broken, the command should **fail to send** — why would it **go to the wrong place**? Connection health and routing correctness are two different things. So I went back to check the "routing table changes during rebuild" step: if redis-py can't find a slot, it throws an exception; it doesn't send randomly. And `aclose()` doesn't clear the routing table either. That step was just an assumption.

**This chain explains why connections were being rebuilt over and over, but it doesn't explain where the MOVEDs came from.** MOVED is the cause, not the effect. I had to look elsewhere.

## 4. Couldn't reproduce it on the bastion host

So I moved to reproduction. The bastion host was in the same VPC and could connect directly to the cluster. I only did read operations.

I created a client with exactly the same constructor parameters as the recommendation service and sent a few hundred read commands: 0 MOVED. Increased concurrency to 256: still 0. Tried pipeline: 0. Added dependencies one by one, like hiredis and ddtrace: still 0.

Then I pointed all 16,384 slots in the routing table to a single shard, simulating the old pre-expansion topology — after about 20 commands, the client repaired itself automatically. That was actually useful information: **a stale routing table could not be the cause**, because the client can fix that on its own, while production had been stuck at 42% for two days.

## 5. A reproduction that didn't hold up

After the bastion path stalled, I tried a different angle: force-refresh topology 33 times per second in the background while sending commands, and measure the increment using the server-side `MOVED` counter.

```
A  no refresh                  MOVED per command = 0.00
B  topology refresh 33/s       MOVED per command = 0.22
```

That looked like a signal. At the time I was ready to go change config in that direction.

But before changing anything, I hooked the client method that handles MOVED, because I wanted to capture what the client thought the slot owner was versus what the server said it was. Result: across 3000 commands, that method was never called once. **My client had not produced a single MOVED.**

So where did the 0.22 in group B come from? What I had measured was the server's global counter, and the production recommendation service itself already had a background rate of 390 MOVEDs per second. In my measurement window, the background value was over nine thousand, and my observed "increment" was only one tenth of that, while production's own fluctuation was already on that scale. **That 0.22 was completely within the noise floor.**

I reran it using client-side counting instead, and both groups were 0.

If you're measuring your tiny signal in a place that already has huge background noise, the result is unreliable. And sometimes the noise gives you a number that looks very convincing.

## 6. I could reproduce the symptom, but not the production cause

Digging further into the source, I found that the routing strategy is decided before client initialization completes: if the client doesn't yet have a `default_node`, the command is treated as a "no-key command", doesn't consult the routing table, and is sent to a randomly chosen node. And the first line of `aclose()` is to set `default_node` to `None`.

So I artificially forced `default_node` to stay `None`, ran at concurrency 300, and counted on the client side:

```
normal                      0.00 / 0.00 / 0.00
default_node = None         0.91 / 0.89 / 0.89     ← persistent, no decay
```

This time I really did reproduce it, and it was persistent. The mechanism itself was valid.

The problem is that **this only proves that "if you break X, you get this symptom" — it does not prove that X was actually broken in production.** So I checked the startup logs from the production containers:

```
22:39:05 | app.core.database_manager:322
  Redis Cluster connection initialized - host=clustercfg.xxx...
```

Initialization had succeeded, and `default_node` is assigned at exactly that step. So production did have a valid `default_node`; the state I had constructed did not exist online.

## 7. One INFO line in the startup logs

But reading the startup logs wasn't wasted effort. Right before that `initialized` line was this:

```
22:39:05 | app.core.database_manager:383
  Redis Cluster address_remap enabled for local development
```

All 8 containers logged this line.

`address_remap` is a redis-py parameter. Under normal circumstances, the cluster client first asks for `CLUSTER SLOTS`, the cluster tells it which slots belong to which nodes and what those node addresses are, and then the client sends commands according to that table. `address_remap` lets you rewrite the node address after receiving it. The implementation in the recommendation service was:

```python
# Address remapping: map cluster-returned private addresses to local port-forwarded addresses (for local development only)
def address_remap(address):
    return (host, port)      # host = clustercfg
```

No matter which node address the cluster returned, it rewrote all of them to the configured `clustercfg` address. **In essence, it hardcoded all node addresses to the same one.**

Its intended use was local development: a laptop connects to the cluster inside the VPC through SSM port forwarding, the cluster returns private IPs, the laptop can't reach them, so everything has to be rewritten back to the tunnel address. The comment said "for local development only", and the code default was `false`. All of that was fine.

So how did it get enabled in production? There was no `REDIS_USER_ADDRESS_REMAP` in the task definition environment variables. Then I checked the repo:

```
.env (committed in git):  REDIS_USER_ADDRESS_REMAP=true
no .dockerignore in repo
Dockerfile:               COPY . .           ← .env gets baked into the image
app/main.py:16            load_dotenv()      ← fills in values from .env for variables that are not set
```

`load_dotenv()` does not override existing environment variables, so the ones explicitly set in ECS were all correct. But ECS did not set `REDIS_USER_ADDRESS_REMAP`, so the local-development `true` from `.env` took effect.

Once enabled, when the cluster answered "slots 0-8191 belong to node A, 8192-16383 belong to node B", remap rewrote both addresses to `clustercfg`. The routing table became:

```
normal:  slot 0-8191 → node A,         slot 8192-16383 → node B
actual:  slot 0-8191 → clustercfg,     slot 8192-16383 → clustercfg
```

The slot calculation was correct, but both results pointed to the same name. When a real connection was created, `clustercfg` DNS round-robined between the two nodes, so the effect was equivalent to randomly picking a shard — half the requests would go to the wrong one.

This time I started with production evidence and then reproduced it:

```
address_remap off    1500 commands   MOVED = 0        routing table = [node A, node B]
address_remap on     1500 commands   MOVED = 1459     routing table = [clustercfg]
```

The two real nodes in the routing table had been collapsed into one.

## 8. Why nothing happened for seven months, and why the API service was fine

I checked with `git log -S`, and both the `address_remap` code and the `true` in `.env` came in through the same commit on 2026-01-28. The incident happened seven months later.

Nothing happened for seven months because **before the scale-out there was only one shard**. `clustercfg` only resolved to that single node, so "rewrite all addresses to clustercfg" was effectively the same as not rewriting anything. On 09-02, when the second shard was added, this config changed from harmless into random routing.

Then it got masked by a more obvious problem — in the previous post, the redis-py 5.0.0 client hang caused all writes to fail, which was much more visible than MOVED. Only after upgrading to 8.x on 09-03 and fixing the hang did MOVED become the remaining curve.

Why was the API service fine? Its initialization code makes it obvious:

```python
if _is_cluster_host(host):              # whether it starts with clustercfg
    _client = RedisCluster(**common)        # prod/stage: cluster client
else:
    _client = aioredis.Redis(**common)      # dev: regular single-node client
```

In the API service, the dev environment connects to a single-node instance with cluster mode disabled, and the client treats it as plain Redis. It doesn't do topology discovery, so the "can't reach private node addresses" problem doesn't exist there. **It never needed the remap config in the first place.** The recommendation service didn't have this branch, and used the cluster client locally too, so it needed remap to deal with private addresses.

One easy point of confusion is worth clarifying here. In the AWS console, all ElastiCache instances are called clusters, but `Cluster mode: Enabled` and `Disabled` are two different things: Disabled is a primary-replica replication group, while Enabled is the actual Redis Cluster protocol. A colleague mentioned that "other services have always connected to cluster through SSM tunnel just fine" — those instances were all Disabled.

## 9. The fix

The fix was the most conservative possible: leave `.env` untouched, and explicitly add `REDIS_USER_ADDRESS_REMAP=false` to the prod and stage task definitions. ECS environment variables have higher priority than `.env`, so this was a four-line change.

I didn't remove `.env` because I checked and found that 14 other variables from it were currently taking effect in production. Removing it could have side effects I couldn't confidently predict; that needed to be handled separately.

After deployment:

| | Before Fix | After Fix |
|---|---|---|
| Read command MOVED ratio | 35–45% | **0** |
| New connections per second | ~880 | **0.1** |
| Provider crashes | 11/minute | **0** |

<center>(Image placeholder: error curves before and after the fix, dropping to 0 after deployment)</center><br>

One note on the last line. The direct cause of the provider crashes was a bug in redis-py on the reconnect path ([#4028](https://github.com/redis/redis-py/issues/4028), fix already merged but not yet released): connections were being repeatedly disconnected and rebuilt, and during the reconnect handshake, a concurrent disconnect could race with it and throw `AttributeError`. It wasn't an independent issue. Once connections stopped being rebuilt over and over, that race condition no longer had a chance to trigger, so it also dropped to zero after the fix.

## 10. Retrospective

**1. Read the logs first, then run experiments**

The most effective step in the whole investigation was reading the startup logs from the prod containers. Once the line `address_remap enabled` showed up, the problem was basically settled. Before that, I had tried more than a dozen combinations on the bastion host, and every one of them was just guessing.

The logs had actually been telling me the answer the whole time. I just hadn't looked first.

**2. Being able to produce the symptom does not mean you've found the cause**

This time, two different hypotheses could both stably reproduce the same MOVED rate as production on the bastion host, and neither one was what was actually happening online. The difference is the direction of evidence: did you first see evidence in production and then reproduce it, or did you first construct a state and then try to match the symptom? There can be many different paths to the same symptom.

**3. In a noisy environment, first ask whether the signal is even separable**

That 0.22 "reproduction" was just noise in the server-side counter. Switching to client-side counting made it 0. In the future, when running experiments in a live-traffic environment, the first question should be: how big is the signal, how big is the noise, and can I separate them? If not, measure somewhere else.

**4. How do you keep local config from leaking into production**

A `.env` committed into git, `COPY . .` baking it into the image, and `load_dotenv` filling in missing values — each of those is common on its own. Together, they mean: any local-only switch will go to production unless ECS explicitly sets it. This time it was `address_remap`; there are still 14 other variables in `.env` in the same state.

The practical fixes are straightforward: exclude `.env` with `.dockerignore`; explicitly list switches in production task definitions instead of relying on defaults; and add environment guards in code for "local only" switches.

## Summary

The root cause was actually very simple: a local-development config hardcoded all node addresses to the same one, and it got carried into production through `.env`. With only one shard, it had no effect. After scaling out to two shards, it turned into random routing, and half the reads went to the wrong node. redis-py rebuilds the entire client every 5 MOVEDs, so connections couldn't live for even 1 second, and the rebuild process then triggered another race condition, causing user profile data to be dropped too.

Four lines of config fixed everything.

But between seeing those tens of millions of MOVEDs and changing those four lines, there was a day and a half, seven or eight hypotheses, and a lot of dead ends. Every hypothesis looked internally consistent at the time, and each could produce some kind of symptom on the bastion host, but none of them matched production once checked against real evidence. The step that finally settled it was simply reading through the container startup logs.

That's probably the most practical lesson from this incident: when debugging a production issue, finish looking at what production is already telling you before you start running experiments.