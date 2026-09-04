---
category: cloud
excerpt: The service was mysteriously getting drained and rebuilt in batches. The
  database looked pretty stable too. After digging into it for quite a while, I finally
  found that a third-party SDK was quietly making a synchronous blocking call inside
  an `async` function, freezing the event loop for several seconds and triggering
  a whole cascading failure chain.
keywords: python, asyncio, event loop, gunicorn, alb, health check, ecs, connection
  pool, timeout
lang: en
layout: post
title: A Synchronous Blocking Call Froze the Entire Event Loop
---

## Introduction

There have been quite a few issues in the service lately, so I’ve been watching the dashboards much more closely than usual. One day, while looking through the memory metrics, I noticed a very strange segment: Min, Average, and even Max—which normally stayed steadily above 70%—all dropped together. All three lines fell all the way down to somewhere near the cold-start baseline, then spent more than half an hour slowly climbing back to normal.

I checked the event history in the container orchestration platform, and during that period, almost all running containers for this service were marked as "unhealthy" and removed/rebuilt in bulk. This wasn’t one or two containers flapping a bit—it was a real batch-scale traffic removal event, which is why even Max got dragged down instead of only Min dropping.

![QQ_1787438497584](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822174144524.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Image placeholder: memory usage Min/Max/Average curves, with all three lines dropping together near the cold-start baseline, then slowly climbing back to normal)</center><br>

I checked the deployment history too. During that time, **nobody deployed anything, and there wasn’t a single release**. The containers were not restarted as part of a "normal new version rollout." If you don’t rule that out completely, nothing you find afterward really stands—because a batch restart could very well have just been caused by an ordinary deployment, and there’d be no need to look elsewhere. Only after confirming this was not deployment-triggered did it make sense to keep digging.

The most confusing part was: the database looked perfectly normal, and the application itself had no OOMs and no worker heartbeat timeout records. **Nothing seemed broken, yet the service was still being judged unhealthy and removed in batches.**

In the end, the culprit turned out to be a very easy-to-miss piece of code: a third-party SDK whose interface was written as `async def`, but whose actual internal call was **pure synchronous blocking**. That one call froze the entire service’s event loop for several seconds, and like knocking over the first domino, it cascaded into the database connection pool, health checks, and eventually large-scale traffic removal and rebuilds. I’m writing down the full investigation process and the underlying mechanics here.

## 1. First, rule out the two most common suspects

The service uses gunicorn + uvicorn workers. When something like this happens, the usual first checks are these two:

- **The system OOM Killer force-killed the process**: if the kernel kills a worker, the gunicorn master process logs a very specific message when it notices the worker disappeared (something like `Worker was sent SIGKILL! Perhaps out of memory?`).
- **The worker itself missed heartbeats and got declared dead**: uvicorn workers periodically "check in" with the gunicorn master process. If the master doesn’t receive heartbeats for a while, it assumes the worker is hung and force-kills/restarts it. The logs would contain `WORKER TIMEOUT`.

I checked how many times those two keywords appeared around the incident window—**not once**. The two most common explanations for "why was the container replaced" both didn’t match.

## 2. Change the angle: who removed the containers?

If the application logs weren’t getting me anywhere, then I needed a different angle—look at the **service events maintained by the container orchestration platform itself** (this information is not in the application logs; it’s a separate operational event stream recorded by the orchestrator).

Once I pulled that up, things started to make sense. In those few minutes, the orchestration platform marked almost all running containers for this service as "unhealthy," and the reason was identical across the board:

```text
(task xxx) is unhealthy in (target-group ...)
due to (reason Request timed out).
```

In other words, the load balancer’s active health checks timed out. The process hadn’t actually died—it was just **responding too slowly to the health check probe, slow enough to exceed the load balancer’s threshold**, so it got removed and rebuilt. And it happened wave after wave: once a few containers were removed, the remaining ones had to absorb more traffic, got even slower, and then more containers were removed. It snowballed.

![QQ_1787438403325](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822174006543.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Image placeholder: orchestration platform event stream screenshot, showing many tasks marked unhealthy and rebuilt due to health check timeouts in a short period)</center><br>

At this point the nature of the issue was basically clear: **the process itself most likely never died; it was just so slow to respond to health checks that an external system misjudged it as dead**. That lines up perfectly with "no OOM, no worker timeout," because those are two completely separate detection mechanisms.

## 3. Trace backward: what exactly was happening during those few seconds?

I looked through the business logs from the tens of seconds before this batch of containers got removed, and found a large number of database errors. The gist was: "all connections in the pool were occupied, waited in queue for 30 seconds and still didn’t get one, so gave up" (`QueuePool limit ... connection timed out`, the standard SQLAlchemy connection pool error).

By itself, that error isn’t unusual. Under high concurrency, a saturated connection pool is nothing new. But the strange part was that **the timestamps of these errors were almost all squeezed into the same sub-second window**, with dozens of them. Under normal circumstances, if the connection pool is exhausted and everyone waits and times out independently, the errors should be spread out—each request enters the queue at a different time, so their 30-second countdowns should expire at different moments. This kind of "all at once" pattern looked wrong. It also matched the earlier observation that "the database itself looked stable": if the database really lacked capacity, the errors should have been more evenly distributed, not clustered.

![QQ_1787438622864](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822174345393.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Image placeholder: timestamp distribution of connection pool timeout errors in logs, with dozens of entries tightly clustered into a very short window)</center><br>

It looked much more like this: "these requests’ countdowns should actually have expired earlier, but the thing responsible for triggering those timeout callbacks stopped functioning normally for a while; then the moment it resumed, all the accumulated callbacks fired at once." In other words: **it wasn’t that the database was insufficient—it was that something froze the event loop that this whole timeout mechanism depended on.**

## 4. Find the real culprit: a call that "looked async but was actually sync"

With the hypothesis that "the event loop got frozen," I went back to check what this service was doing at the time, focusing specifically on places where code was **written inside `async def`, but the actual internal call was synchronous blocking** (this kind of code can fool the eye, but not the event loop—`async`/`await` does not automatically turn an ordinary synchronous function call into a non-blocking one).

I found one. The project had integrated the official SDK of a third-party AB testing / feature flag platform a long time ago. Judging from the commit history, this wrapper code was written pretty early, back when traffic was probably much lower than it is now, so this kind of synchronous blocking call likely went unnoticed for a long time. The codebase came from multiple contributors, and the overall quality was uneven. A pitfall like this—"looks async, actually sync"—wasn’t something anyone intentionally left behind; it was more like historical baggage that nobody paid much attention to, until recent traffic growth amplified it into a real avalanche. The wrapper looked roughly like this:

```python
class ExperimentManager:
    _client = None

    @classmethod
    async def fetch_variants(cls, *, device_id, user_id) -> dict:
        """docstring 里写着"用线程避免阻塞事件循环"……"""
        if cls._client is None:
            return {}
        user = User(device_id=device_id, user_properties={...})
        # 这一行是纯同步调用，SDK 内部走的是同步 HTTP 客户端
        variants = cls._client.fetch_v2(user)
        return {k: v.value for k, v in (variants or {}).items()}
```

The docstring sounded great—"use a thread pool to avoid blocking the event loop"—but in the actual code there was no `asyncio.to_thread`, nor any kind of thread scheduling at all. `cls._client.fetch_v2(user)` was just a plain synchronous method call executed in place. The SDK itself was configured with "3-second timeout, retry once on failure, backoff 0.3–2 seconds before retry, then another 3 seconds for the retry," so a single call could theoretically take several seconds.

I checked the SDK’s own failure logs. Under normal conditions they were almost zero, but during the incident minute, failures shot up into the hundreds. And the timing of that spike happened to land **before** the clustered database connection pool errors.

![QQ_1787438672246](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822174434716.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Image placeholder: bar chart of this third-party SDK’s failure logs aggregated by minute, spiking to hundreds in one minute while adjacent minutes stay in single digits)</center><br>

The timing across the three evidence chains lined up: **this synchronous call blocked the event loop first → during that period, everything relying on event-loop scheduling (waiting for DB connections, responding to health checks) got delayed → the moment the event loop resumed, a batch of timeouts exploded all at once → health checks couldn’t be answered → the load balancer judged them timed out → the orchestration platform started removing containers.**

## 5. One remaining question: why did the downstream storm last longer than the trigger itself?

When I put the two timelines side by side, one thing looked asymmetric: that SDK’s failure logs only exploded within a single minute, then disappeared completely after that; but the database connection pool timeout errors only really got started after that minute ended, and kept going for nearly ten minutes, eventually totaling more than 70,000 errors.

One thing needs to be made clear first: **the database itself did not have a problem during this period**—core metrics like connection count and CPU stayed stable the whole time. These errors were entirely from the application-side connection pool failing to get a slot and giving up on its own (`QueuePool` is maintained inside the SQLAlchemy application process itself; it is not the database’s physical connection count being exhausted). This had nothing to do with database capacity. **It was an application-layer problem.**

So the question becomes: if the trigger only caused trouble for one minute, why did the downstream application-layer errors last ten times longer?

Looking closely at the distribution of connection pool errors during that period, it wasn’t one single explosion and then done. There were 5 distinct peaks over roughly ten minutes, each separated by about 2 minutes. The overall shape was "small initial rise, then two or three waves reaching the highest point, then gradual decay." It was rhythmic oscillation, not random noise. There were probably two mechanisms layered together behind it:

**First layer: avalanche feedback caused by traffic removal.** After Amplitude froze the event loop that one time, the first batch of containers got removed and rebuilt because they couldn’t answer health checks. The traffic they had been carrying shifted onto the remaining containers. Those remaining containers suddenly had to handle more requests, so competition for the connection pool naturally became more intense. Then more containers got judged unhealthy because of slower responses and were removed as well. Once this feedback loop starts spinning, it can sustain oscillation for a while even without Amplitude continuing to add fuel, until the number of removed/rebuilt nodes reaches some equilibrium. This also explains why the errors came in waves: each wave roughly corresponds to one cycle of "removal → impact → more removal," matching the cadence of health checks plus the orchestrator’s node rebuild cycle.

**Second layer: restarts themselves were creating new resource pressure.** When a container gets removed and rebuilt, the first thing the new container has to do is **rebuild the entire connection pool from scratch**. Those connections don’t magically exist just because a number is written in the config—they have to establish real TCP connections one by one and go through database authentication handshakes. If a batch of containers restarts in a short period, those new containers all compete to establish a large number of new connections at nearly the same time. That "creating connections" action itself takes time and can queue up, which is effectively another round of contention piled on top of already stressed resources, further extending recovery time.

In other words, that one synchronous Amplitude call merely **knocked over the first domino**. After it stopped, the chain reaction already had its own inertia. The two mechanisms above had to burn themselves out before things could truly settle down. That’s what makes this kind of avalanche failure so nasty: the root cause may only act up for one minute, but cleaning up the aftermath can take ten times longer.

## 6. Break down the mechanics: why can one synchronous call drag so many things down together?

There are a few details here that I repeatedly verified during the investigation, and they’re worth calling out separately.

### 1. "Written inside an async function" does not mean "this line of code is asynchronous"

`async`/`await` only suspends a coroutine and yields control at an actual `await` expression. If you directly call an ordinary synchronous blocking function inside the function body (with no `await`, because it isn’t awaitable at all), Python will not automatically insert a suspension point just because the outer function is `async def`—it just executes normally, waits normally, and returns normally.

The key point is: the `asyncio` event loop runs on **a single thread** the whole time, and all coroutines take turns executing on that one thread. A real asynchronous wait gives control back to that thread so it can schedule other coroutines; a naked synchronous call, on the other hand, **occupies that one and only thread in place** until it returns. During that time, the thread can do nothing else, including scheduling other coroutines or accepting new connections.

### 2. If we rewrote the health check endpoint as synchronous, could that avoid frequent task removal?

Based on the analysis above, this is really a two-layer issue: **first, the event loop really was blocked for those few seconds**—that’s just a fact; there’s no way around it. **Second, tasks were judged unhealthy because they couldn’t answer health checks, and that traffic removal in turn amplified the subsequent congestion**—that’s the nearly ten-minute avalanche described in the previous section.

So the question needs to be phrased more precisely: **if the health check endpoint were implemented synchronously, could it at least still respond during those few seconds when the event loop was blocked, thereby avoiding the task being judged unhealthy, avoiding traffic removal, and cutting off the avalanche chain at the source?**

The answer is still no, for the same reason as before: regardless of whether an endpoint is ultimately implemented synchronously or asynchronously, **the very first step when a request arrives always has to go through the event loop**. The event loop is what listens on the port, accepts the new connection, parses the HTTP request, and only then can we even talk about "should this endpoint run directly, or be handed off to a thread pool?" If the event loop can’t get through that first step, it never even reaches the point of "hand it to the thread pool." So even if the health check endpoint were rewritten as synchronous, during those few seconds when the event loop was truly frozen, it still wouldn’t be able to answer, would still be judged unhealthy, and would still be removed from traffic. This avalanche chain cannot be cut off at the level of "is the endpoint sync or async"—that path simply doesn’t work.

### 3. Why did the timeouts explode in a cluster?

Database connection pool queue timeouts are generally implemented underneath using the event loop’s timer mechanism ("invoke a callback after N seconds to check whether the resource became available"), so they also depend on the event loop continuing to run in order to fire on time. While the event loop is frozen, all the timers that should have expired one after another just sit there. The moment the event loop resumes, they all fire in a batch—that’s the cause of the "clustered explosion" pattern.

This is also a useful signal for judging whether "the event loop may have been frozen": **if a large number of the same kind of timeout errors are squeezed into one very short window instead of being evenly distributed, you can strongly suspect a scheduling-layer problem rather than actual resource pressure being that severe.**

### 4. Process heartbeat ≠ response time of a single endpoint

Gunicorn decides whether a worker is "alive" based on whether that worker is sending heartbeats on time. That is a **process-level liveness check**, which is a completely different dimension from how long any specific request has been running. As long as the event loop itself is still scheduling normally, the heartbeat can continue on time. Even if a request runs for several minutes, as long as it is "politely awaiting" rather than "hogging the thread with a naked synchronous call," the process heartbeat is unaffected, and gunicorn won’t kill the worker.

Conversely, **"process heartbeat is normal" can never prove that "every endpoint is responding in time"**. Those are two independent things. Relying on one mechanism to cover for the other is itself an architectural blind spot that’s easy to overlook.

## 7. Fix strategy

What actually needed fixing was that "fake async" call: just honestly move it into a thread pool:

```python
variants = await asyncio.to_thread(cls._client.fetch_v2, user)
```

With this change, even if the SDK call really blocks for several seconds, it only occupies one thread slot in the thread pool. The event loop itself remains completely unaffected, and other coroutines—including health checks—continue to be scheduled normally.

While I was at it, I also revisited the relationship between several internal timeout values: the database connection pool queue timeout, the load balancer’s health check threshold, and gunicorn’s own worker heartbeat timeout. Originally they had all been chosen more or less by gut feel, and by coincidence they landed in the same order of magnitude. Once resource pressure actually happened, several mechanisms fired almost simultaneously and reinforced each other into "it really is dead," which amplified the avalanche effect instead.

Afterward, I reworked the priority of these values according to the principle that **the mechanism with the smaller blast radius should always fail first**: local resource wait timeouts should be clearly shorter than process-level watchdog timeouts. That way, under resource pressure, what happens first is always "this one request fails gracefully," rather than escalating to a much more violent mechanism like "kill the whole process and take a bunch of otherwise healthy requests down with it."

## Summary

The biggest takeaway from this investigation was finally separating two concepts that are easy to blur together: **process liveness** and **single-request health**. They are two independent mechanisms. One only cares whether "the event loop is still turning," while the other cares "how long this specific request has been running." Neither can substitute for the other.

The other, more straightforward lesson is: **`async def` is only a syntactic shell; it does not automatically verify whether the calls inside are truly asynchronous.** When integrating a third-party SDK, even if the docs or docstring confidently claim "this already runs in a thread and won’t block," it’s still worth taking the time to inspect whether that is actually true underneath—especially for old wrapper code that may not have kept pace with the rest of the project’s async evolution. Those are exactly the kinds of places where this sort of "fake async" likes to hide. And once you really step on it, the cost is often not just "this one endpoint gets a bit slower," but, like this time, dragging a whole pile of seemingly unrelated mechanisms down together along the event loop’s single scheduling axis.