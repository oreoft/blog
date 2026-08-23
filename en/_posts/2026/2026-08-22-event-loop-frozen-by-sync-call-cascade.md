---
category: cloud
excerpt: 'The service was mysteriously being drained and rebuilt in batches. The database
  looked pretty stable too, so after digging around for quite a while, I finally found
  the culprit: a third-party SDK was quietly making a synchronous blocking call inside
  an `async` function, freezing the event loop for several seconds and triggering
  a whole cascading failure chain.'
keywords: python, asyncio, event loop, gunicorn, alb, health check, ecs, connection
  pool, timeout
lang: en
layout: post
title: 'An Avalanche Investigation: One Synchronous Blocking Call Froze the Entire
  Event Loop'
---

## Introduction

There have been quite a few issues with the service lately, so I’ve been watching the monitoring dashboards much more frequently than usual. One day, while looking through the memory charts, I noticed a very strange segment: Min, Average, and even Max—which normally stayed steadily above 70%—all dropped together. All three lines fell all the way down to somewhere near the cold-start baseline, then spent more than half an hour slowly climbing back to normal levels together. I checked the event records in the container orchestration platform, and during that period, almost every running container for this service had been marked as "unhealthy" and removed and rebuilt in bulk. This wasn’t one or two containers flapping—it was a real batch-scale traffic removal event, which is why even Max got dragged down instead of only Min dropping.

![QQ_1787438497584](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822174144524.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Image placeholder: memory usage Min/Max/Average curves, with all three lines dropping together near the cold-start baseline, then slowly climbing back to normal levels together)</center><br>

I checked the deployment history, and during that period, **nobody deployed anything, and there wasn’t a single release**. The containers were not restarted as part of a "normal new version rollout." If you don’t rule that out completely, nothing you find afterward really stands—because a batch restart could very well just be caused by an ordinary deployment, and there’d be no need to look elsewhere. Only after confirming that this was not deployment-triggered did it make sense to continue digging.

The most baffling part was that everything looked fine on the database side, and the application itself had no OOMs and no records of worker heartbeat timeouts. **The service didn’t seem broken anywhere, yet it was still being judged unhealthy and removed in batches.**

In the end, the culprit turned out to be an easy-to-miss piece of code: a third-party SDK whose interface was written as `async def`, but whose actual internal call was **pure synchronous blocking**. That single call froze the entire service’s event loop for several seconds, and like knocking over the first domino, it cascaded into the database connection pool, health checks, and eventually large-scale traffic removal and rebuilding. I’m writing down the full investigation process and the reasoning behind it.

## 1. First, rule out the two most common suspects

The service uses gunicorn + uvicorn workers. When something like this happens, I usually check two things first:

- **The system OOM Killer force-killed the process**: if the kernel kills a worker, the gunicorn master process will log a very specific message after noticing the worker disappeared (something like `Worker was sent SIGKILL! Perhaps out of memory?`).
- **The worker itself was declared dead due to heartbeat timeout**: uvicorn workers periodically "check in" with the gunicorn master process. If the master doesn’t receive heartbeats for a while, it assumes the worker is stuck, force-kills it, and restarts it. In that case, the logs will contain `WORKER TIMEOUT`.

I checked how many times these two keywords appeared around the incident window—**not once**. The two most common explanations for "why containers got replaced" both didn’t match.

## 2. Change the angle: who removed the containers?

Since the application logs weren’t getting me anywhere, I switched perspectives and checked the **service events maintained by the container orchestration platform itself** (this information is not in the application logs; it’s a separate operational event stream recorded by the orchestrator).

Once I pulled that up, things started to make sense. During those few minutes, the orchestration platform marked almost all running containers of this service as "unhealthy," all for the exact same reason:

```text
(task xxx) is unhealthy in (target-group ...)
due to (reason Request timed out).
```

In other words, the load balancer’s active health check probes timed out. The process hadn’t actually crashed—it was just **responding to the health check probe too slowly, slow enough to exceed the load balancer’s threshold**, so it got removed and rebuilt. And it happened wave after wave: after a few containers were removed, the remaining ones had to handle more traffic, got even slower, and then more containers were removed. It snowballed.

![QQ_1787438403325](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822174006543.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Image placeholder: screenshot of the orchestration platform event stream, showing many tasks marked unhealthy and rebuilt in a short period due to health check timeouts)</center><br>

At this point, the nature of the issue was basically clear: **the process itself most likely didn’t die; it just responded to health checks so slowly that an external system misjudged it as dead**. That lines up perfectly with "no OOM, no worker timeout," because those are two completely separate detection mechanisms.

## 3. Trace backward: what exactly was it busy doing during those few seconds?

Looking through the business logs from the tens of seconds before this batch of containers got removed, I found a large number of database errors. The rough meaning was: "all connections in the pool were occupied, waited in queue for 30 seconds and still didn’t get one, so gave up" (`QueuePool limit ... connection timed out`, the standard SQLAlchemy connection pool error).

By itself, that error isn’t unusual. Under high concurrency, a saturated connection pool is nothing new. But the weird part was that **the timestamps of these errors were almost all squeezed into the same sub-second window**, with dozens of them. Under normal circumstances, if the connection pool is full and requests are each waiting and timing out independently, the errors should be spread out—because each request starts waiting at a different time, and each 30-second countdown should expire at a different moment. This "all bunched together" shape looked wrong. It also matched the earlier observation that "the database itself looked stable": if the database really lacked capacity, the errors should have been more evenly distributed, not clustered.

![QQ_1787438622864](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822174345393.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Image placeholder: distribution of connection pool timeout error timestamps in the logs, with dozens of entries concentrated into the same extremely short window)</center><br>

It looked much more like this: "these requests’ countdowns should actually have expired earlier, but the thing responsible for triggering those timeout callbacks stopped functioning normally for a while, and only when it resumed did all the accumulated callbacks fire at once." In other words: **it wasn’t that the database was insufficient; something had frozen the event loop that carried this whole timeout mechanism for a period of time.**

## 4. Find the real culprit: a call that "looked async but was actually sync"

With the hypothesis that "the event loop was frozen," I went back to check what this service was doing at the time, focusing specifically on places that were **written inside `async def` but actually made synchronous blocking calls internally**. This kind of code can fool the eye, but not the event loop—`async`/`await` does not automatically turn an ordinary synchronous function call into a non-blocking one.

I found one. A long time ago, the project integrated the official SDK of a third-party AB testing / feature flag platform. Judging from the commit history, this wrapper code was written pretty early on, when traffic was probably much lower than it is now, so this kind of synchronous blocking call likely went unnoticed for a long time. The codebase was written by different people over time, and the overall quality varied quite a bit. A trap like this—"looks async, actually sync"—wasn’t something someone intentionally left behind so much as historical baggage that nobody paid much attention to, until recent traffic growth amplified it into a real avalanche. The wrapper code looked roughly like this:

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

The docstring sounded great—"use a thread pool to avoid blocking the event loop"—but the actual code had no `asyncio.to_thread` and no thread scheduling of any kind. `cls._client.fetch_v2(user)` was just a plain synchronous method call executed right there. The SDK itself was configured with "3-second timeout, retry once on failure, back off 0.3–2 seconds before retrying, then give the retry another 3 seconds," so in theory a single call could take several seconds.

I checked the SDK’s own failure logs. Under normal conditions, they were almost zero. But during the minute of the incident, the failure count spiked straight into the hundreds—and that surge happened **before** the clustered explosion of database connection pool errors.

![QQ_1787438672246](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822174434716.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Image placeholder: bar chart of this third-party SDK’s failure logs aggregated by minute, spiking into the hundreds in one minute while the surrounding minutes only have single-digit counts)</center><br>

The timing of the three evidence chains lined up perfectly: **this synchronous call blocked the event loop first → during that time, everything relying on event loop scheduling (waiting for DB connections, waiting to answer health checks) got its queueing time stretched out → the moment the event loop resumed, a batch of timeouts exploded all at once → health checks couldn’t be answered → the load balancer judged them as timed out → the orchestration platform started removing containers.**

## 5. One remaining question: why did the downstream storm last much longer than the trigger?

Putting the two timelines side by side, one thing looked asymmetric: the SDK failure logs only exploded within a single minute, then disappeared completely after that; but the database connection pool timeout errors only really got started after that minute ended, and kept going for nearly ten minutes, eventually totaling more than 70,000 errors. One thing needs to be made clear first: **the database itself had no problem during this period**—core metrics like connection count and CPU stayed very stable throughout. These errors were entirely from the application-side connection pool failing to get a slot after waiting and then giving up (`QueuePool` is the pool maintained by SQLAlchemy inside the application process, not the database’s physical connection count being maxed out), so this had nothing to do with database capacity. **This was an application-layer problem.**

So the question becomes: if the trigger only caused trouble for one minute, why did the downstream application-layer errors last ten times longer?

Looking closely at the distribution of connection pool errors during that period, it wasn’t a one-time explosion and then done. There were 5 distinct peaks over about ten minutes, roughly 2 minutes apart. The overall shape was "small initial rise, then two or three waves reaching the highest point, then gradual decay toward the end"—a rhythmic oscillation, not random noise. Most likely, this was two mechanisms layered together:

**First layer: avalanche feedback caused by traffic removal.** After that Amplitude call froze the event loop, the first batch of containers got removed and rebuilt because they couldn’t answer health checks. The traffic they had been carrying shifted onto the remaining containers—so those remaining containers suddenly had to handle more requests, naturally making connection pool contention worse. Then even more containers got judged unhealthy due to slower responses and got removed too. Once this feedback loop starts spinning, it can sustain oscillation for a while even without Amplitude continuing to cause trouble, until the number of removed/rebuilt nodes reaches some balance point. This also explains why the errors came in waves: each wave roughly corresponds to one cycle of "removal → impact → more removal," matching the cadence of health checks plus orchestration rebuild timing.

**Second layer: restarts themselves create new resource pressure.** When a container gets removed and rebuilt, the first thing the new container has to do is **rebuild its entire connection pool from scratch**. Those pool connections don’t magically exist just because a number is written in config—they have to actually establish TCP connections one by one and go through database authentication handshakes. If a batch of containers restarts in a short period, those new containers will all race to establish a large number of new connections almost simultaneously. That "building connections" process itself takes time and queues up, effectively adding another round of contention on top of already stressed resources, which further lengthens recovery time.

In other words, that one synchronous Amplitude call merely **knocked over the first domino**. After it stopped, the chain reaction already had its own inertia, and the two mechanisms above had to burn themselves out before things could truly settle down. That’s what makes this kind of avalanche failure so nasty: the root cause may only be active for one minute, but cleaning up the mess can take ten times longer.

## 6. Let’s unpack the mechanics: why can one synchronous call drag so many things down with it?

There are a few details here that I repeatedly verified during the investigation, and they’re worth calling out separately.

### 1. "Written inside an async function" does not mean "this line of code is asynchronous"

`async`/`await` only suspends a coroutine and yields control at an actual `await` expression. If you directly call an ordinary synchronous blocking function inside the function body (with no `await`, because it isn’t awaitable at all), Python will not automatically insert a suspension point just because the outer function is `async def`—it just executes normally, waits normally, and returns normally.

The key point is that `asyncio`’s event loop runs on **a single thread** the whole time, with all coroutines taking turns on that one thread. A real asynchronous wait hands control back to that thread so it can schedule other coroutines; a naked synchronous call, on the other hand, **occupies that only thread in place** until it returns. During that time, the thread cannot do anything else, including scheduling other coroutines or accepting new connections.

### 2. If we changed the health check endpoint to synchronous, could that avoid tasks being removed so frequently?

Based on the previous section, this is actually a two-layer issue: **first, the event loop really was genuinely blocked for those few seconds**—that’s just a fact; there’s no way around it. **Second, tasks were judged unhealthy because they couldn’t answer health checks, and that traffic removal in turn amplified the subsequent congestion**—that’s the nearly ten-minute avalanche described above.

So the question needs to be phrased more precisely: **if the health check endpoint were implemented synchronously, could it at least still respond normally during those few seconds when the event loop was blocked, thereby avoiding tasks being judged unhealthy and removed, and cutting off the avalanche chain at the source?**

The answer is still no, for the same reason as before: regardless of whether an endpoint is ultimately implemented synchronously or asynchronously, **the very first step of handling an incoming request always has to go through the event loop**. The event loop is what listens on the port, accepts the new connection, parses the HTTP request, and only then can it even get to the question of "should this endpoint run directly, or be handed off to a thread pool?" If the event loop can’t get past that first step, it never even reaches the point of "hand it to the thread pool." So even if the health check endpoint were changed to synchronous, during those few seconds when the event loop was truly frozen, it still wouldn’t be able to answer, would still be judged unhealthy, and would still be removed. This avalanche chain cannot be cut off at the level of "sync vs async endpoint implementation"—that path simply doesn’t work.

### 3. Why did the timeouts explode in a cluster?

The queue timeout for the database connection pool is generally implemented underneath using the event loop’s timer mechanism ("call back after N seconds and check whether the resource has become available"), which also depends on the event loop continuing to run in order to fire on time. While the event loop was frozen, all the timers that should have expired one after another just sat there. Only when the event loop resumed did they all fire in a batch at once. That’s exactly what caused the "clustering" phenomenon, and it’s also a very useful signal when diagnosing whether "the event loop may have been frozen": **if a large number of the same kind of timeout errors are squeezed into the same extremely short window instead of being evenly distributed, you can strongly suspect a scheduling-layer problem rather than actual resource pressure being that severe.**

### 4. Process heartbeat ≠ response time of a single endpoint

When gunicorn decides whether a worker is "alive," it looks at whether that worker is sending heartbeats on time. That is a **process-level liveness check**, which is a different dimension from how long any specific request takes. As long as the event loop itself is still scheduling normally, heartbeats can still be sent on time. Even if a request runs for several minutes, as long as it is "properly awaiting" rather than "hogging the thread with a naked synchronous call," the process heartbeat is unaffected, and gunicorn won’t kill that worker.

Conversely, **"process heartbeat is normal" can never prove that "every endpoint is responding in time"**—those are two separate things, and relying on one mechanism to cover for the other is itself an architectural gap that’s easy to overlook.

## 7. Fix strategy

What really needed fixing was that "fake async" call: just honestly move it into a thread pool.

```python
variants = await asyncio.to_thread(cls._client.fetch_v2, user)
```

With this change, even if that SDK call really blocks for several seconds, it only occupies one thread slot in the thread pool. The event loop itself remains completely unaffected, and other coroutines—including health checks—continue to be scheduled normally.

While I was at it, I also revisited the relationship between several internal timeout values: the database connection pool queue wait timeout, the load balancer’s health check threshold, and gunicorn’s own worker heartbeat timeout. Originally, they had all been chosen more or less by gut feel, and by coincidence they landed in roughly the same order of magnitude. Once resource pressure actually happened, multiple mechanisms fired almost at the same time and reinforced each other into "it’s really dead," which amplified the avalanche effect. Afterward, I reworked the priority of these values based on the principle that **the mechanism with the smaller blast radius should always fail first**: local resource wait timeouts should be clearly shorter than process-level watchdog timeouts, so that under resource pressure, what happens first is always "this one request fails gracefully," rather than escalating to "kill the whole process and take a bunch of unrelated healthy requests down with it."

## Summary

The biggest takeaway from this investigation was finally separating two concepts that are easy to blur together: "process liveness" and "single-request health." They are two independent mechanisms. One only cares whether **the event loop is still turning**, while the other cares **how long this specific request has been running**. Neither can substitute for the other.

The other, more straightforward lesson is this: **`async def` is only a syntactic shell; it does not automatically verify whether the calls inside the function body are truly asynchronous.** When integrating a third-party SDK, even if the docs or docstring confidently claim "this already runs in a thread and won’t block," it’s still worth taking the time to check whether that is actually true underneath—especially for old wrapper code that may not have kept up with the rest of the project’s async evolution. Those are often exactly where this kind of "fake async" likes to hide. And once you really step on one, the cost is often not just "this one endpoint gets a bit slower," but, like this time, dragging a whole pile of seemingly unrelated mechanisms down together along the event loop—the one and only scheduling axis.