---
category: middleware
excerpt: 'While investigating a slow memory leak in a service, I came across a piece
  of background enrichment logic a teammate had written: on every call, it instantiated
  a brand-new `AsyncOpenAI` client, and the connection pool quietly piled up into
  a leak. I wanted to simply cache and reuse the client, but it turned out that didn’t
  work at all—the root cause was the lifecycle of the event loop.'
keywords: python, asyncio, openai, httpx, event loop, memory leak, threadpool
lang: en
layout: post
title: 'Investigating a Slow Memory Leak: Creating a New OpenAI Client Every Time,
  with the Real Issue in the Event Loop'
---

## Introduction

Recently, I was investigating a slow memory leak in one of our services. After watching the memory curve in production, I noticed the process RSS was steadily creeping upward. It didn’t look like the stepwise growth you’d expect from increasing business data volume. Instead, it was that kind of "slow but constant" diagonal line that just keeps going no matter how long you wait. Given enough runtime, it was clearly going to hit the container memory limit.

This was actually pretty obvious in monitoring, but it hadn’t turned into a real incident yet—mainly because the business iterates quickly, and we deploy basically every day. Each deployment restarts the machines, and RSS gets reset back to baseline every time, so the leak never had enough time to accumulate all the way to the top before being dragged back to the starting point. But that doesn’t mean the problem wasn’t there. Extend the curve far enough and the conclusion is obvious: as long as the service runs continuously for long enough without restarting, sooner or later it will hit the container memory limit. At that point, either gunicorn will decide memory usage is too high and start killing workers, or some lower-level mechanism will kill it more forcefully. Frequent releases were only delaying the inevitable by accident.

![QQ_1787376366426](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822002614538.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Image placeholder: memory leak curve, RSS keeps climbing over time without converging, eventually approaching the container memory limit during long-running execution)</center><br>

After tracing through the code, I found the culprit was a piece of "asset enrichment" logic a teammate had written earlier: when a user uploads an asset, the backend calls an LLM to do tagging and classification, then computes an embedding and writes it into the search index. This logic itself isn’t fast, and we didn’t want it occupying the main thread’s event loop—after all, the main loop still needs to handle incoming requests normally, and nobody wants a single LLM call to stall the whole service. So the original idea was to throw this work into a dedicated background thread pool. That idea itself was fine. The problem was in how the async SDK was being called inside the thread pool. That’s where a subtle trap got buried.

This post is a record of how I investigated it, why this client couldn’t just be reused directly, and what solution we ended up shipping.

## 1. The original approach: start another event loop inside the thread pool

First, here’s roughly what the original code looked like:

```python
def submit_background_job(coro_func, *args, **kwargs):
    # Throw it into the thread pool so the current request isn't blocked
    executor.submit(asyncio.run, coro_func(*args, **kwargs))

async def enrich_asset(asset_id: int):
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    resp = await client.chat.completions.create(...)
    ...
```

It’s not hard to guess why someone would write it this way: the main service is built on an async framework, but the enrichment logic needs to call an external LLM API, and we still wanted to keep using the async SDK style of programming (retries, timeouts, streaming, etc. are already built into the SDK, so there’s no need to wrap a separate sync version ourselves). So the implementation picked a very common combination: **inside each thread from the thread pool, use `asyncio.run()` to spin up a separate event loop, and then `await` the async SDK inside that loop**. This way it doesn’t occupy the main service’s event loop, while still letting us keep the async style. On the surface, it looks like the best of both worlds.

## 2. The cost: you have to create a brand-new client every time

What `asyncio.run(coro)` does is: create a new event loop, run the coroutine, then destroy that loop. In other words, in the code above, every call to `enrich_asset` goes through a full cycle of "create a brand-new loop -> use it once -> throw it away."

The problem starts at this line: `AsyncOpenAI(api_key=..., base_url=...)`. Under the hood, this client wraps an `httpx.AsyncClient`, and `httpx.AsyncClient` internally maintains a real connection pool plus SSL handshake context. Those things are **bound to the event loop they were created on**. Since every call runs on a brand-new loop, the client is naturally one-shot as well—it can’t really be reused after this request, because the next request will run on a completely different new loop. So the code chose the "seems easiest" option: just create a fresh one every time.

But as soon as `AsyncOpenAI` is instantiated, it really does allocate the underlying connection pool (even if no request is ever sent). If you create one every time and then leave it to GC after use, in theory that connection pool and its SSL context should be reclaimed together with that event loop. But in practice, cleanup wasn’t happening cleanly. At the time, I pulled a long-window container memory curve from Datadog—about 14 hours—and the fitted numbers looked like this:

| Metric | Value |
| :--- | :--- |
| Overall memory growth rate over 14 hours | **about 393 MB/h** |
| Total net memory increase over 14 hours | **about 5.35 GB** |
| Peak memory per instance | **about 13.4 GB** (close to the 16 GB container limit) |

I also ran a simple stress test script that repeatedly hit this enrichment path. The memory curve climbed almost in lockstep with the number of calls and never stopped. It had nothing to do with business data volume. That basically confirmed it: **the leak point was this client that was "created fresh every time and never reused"**, and at this growth rate, the container would eventually be eaten alive by this logic itself.

## 3. So why not just reuse the client directly?

Once you see "creating a new client every time," the obvious question is: **why not just cache the client and reuse a single global instance?**

```python
_client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

async def enrich_asset(asset_id: int):
    resp = await _client.chat.completions.create(...)
    ...
```

The answer is: with the current execution model, **it simply cannot be reused**. The reason goes back to the previous section: the `httpx.AsyncClient` inside `AsyncOpenAI` is bound to the event loop that existed at the moment it was created. And in this service, background tasks are run via `asyncio.run()`, which means every call to `enrich_asset` runs on a brand-new event loop, different from the previous one. Even if you store the client in a global variable, it can only be created on **the loop from the first call**—and that loop is destroyed immediately after use. All later loops would then be trying to send requests through a client that is effectively "attached to a dead loop." At the mechanism level, that’s simply wrong. Resources from different event loops can’t be shared across them like that.

In other words, **the prerequisite for "reusing the client" is first having an event loop that itself can be reused**. As long as every task still creates a fresh loop and throws it away, the client has nowhere stable to "live," so caching it or not makes no real difference.

## 4. The fix: don’t touch business logic, bind the thread pool to long-lived event loops and reuse them

The constraint I set for this fix was: **don’t modify the `enrich_asset` business logic itself**. How it calls the LLM and how it processes the result should remain unchanged. The only thing to change is the outer execution layer—how this logic gets run. Since the client must be bound to a fixed event loop in order to be safely reused, the solution should be inverted: **instead of creating a throwaway loop for every task, give each thread in the thread pool its own long-lived event loop, and run all tasks dispatched to that thread on the same loop.**

The concrete implementation uses thread-local storage (`threading.local`) to keep a persistent `asyncio.Runner` per worker thread (`asyncio.Runner` was introduced in Python 3.11+ as a persistent event loop wrapper; functionally it’s equivalent to manually maintaining an event loop that isn’t destroyed):

```python
import threading
import contextvars
from concurrent.futures import ThreadPoolExecutor

_state = threading.local()  # each thread has its own .runner

def _get_runner() -> "asyncio.Runner":
    runner = getattr(_state, "runner", None)
    if runner is None:
        runner = _state.runner = asyncio.Runner()
    return runner

def _run_on_worker_loop(ctx, coro_fn, args, kwargs):
    return _get_runner().run(coro_fn(*args, **kwargs), context=ctx)

executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bg-worker")

def submit(coro_fn, *args, **kwargs):
    ctx = contextvars.copy_context()
    return executor.submit(_run_on_worker_loop, ctx, coro_fn, args, kwargs)
```

With this setup, every task running on the same thread uses **the same event loop**. Once that prerequisite is in place, client caching finally becomes valid:

```python
_clients = {}  # (id(loop), api_key, base_url) -> client

def get_client(api_key: str, base_url: str):
    loop = asyncio.get_running_loop()
    key = (id(loop), api_key, base_url)
    client = _clients.get(key)
    if client is None:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        _clients[key] = client
    return client
```

Including `id(loop)` in the cache key is basically saying: "this client may only be used on the loop it was created on; different loops maintain their own separate instances." Since each thread in the thread pool now has exactly one long-lived loop, the practical effect is that **the whole process will only ever have as many clients as the thread pool size**—for example, 4 threads means 4 clients—instead of growing without bound as the number of calls increases.

When the process exits or the thread pool shuts down, remember to close the client on **that thread’s own loop** (`await client.close()`). Don’t directly close another thread’s connection pool across threads, or you may run into some very weird errors.

That leads to the core conclusion of this fix: **"Can an async client be reused?" is fundamentally the same question as "Can the event loop behind it be reused?"** The two are tightly coupled. Client caching only becomes meaningful once the event loop itself is long-lived and reusable.

## 5. Results

After deploying the fix, I compared two runtime windows of similar length—both around 14 hours:

| Metric dimension | Before fix | After fix | Change |
| :--- | :--- | :--- | :--- |
| Growth rate over 14 hours | about 393 MB/h | about 210 MB/h | **down about 47%** |
| Total net memory increase over 14 hours | about 5.35 GB | about 2.99 GB | **net increase reduced by about 44%** |
| Peak memory per instance (14h) | about 13.4 GB (close to 16 GB limit) | about 9.4 GB | about 6.5 GB of safety margin left |

![QQ_1787326277575](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822002808695.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Image placeholder: overlay comparison of memory curves before and after the fix over similar runtime windows, with a clearly reduced slope)</center><br>

The growth rate was cut almost in half, and the peak moved completely out of the danger zone near the container limit. So the biggest part of the problem was effectively contained.

## Summary

At the end of the day, this whole issue boils down to one sentence: **"Can an async client be reused?" is really asking "Can the event loop behind it be reused?"** The two are tightly bound together, and you can’t solve only the surface-level part.

A few takeaways worth writing down:

- `asyncio.run()` creates a brand-new event loop every time. Wrapping each background task with it is a very common convenience pattern, but if the task uses resources that are bound to the event loop (connection pools, SSL contexts), this "one-shot loop" model makes those resources impossible to safely reuse. The result is that you have to recreate them every time, and the cost is connection-pool leakage.
- On the flip side, simply turning the client into a global singleton doesn’t necessarily help. If the event loop itself is still one-shot, then the global singleton just gets permanently bound to the already-dead loop from the first call, and becomes unusable.
- The correct order is to **first make the event loop long-lived and reusable** (for example, by binding a persistent loop to each thread in the thread pool), and only then cache resources that are bound to that loop. That’s the real fix.
- Even after deploying the fix, I didn’t assume the story was over. The growth rate was cut in half, but the curve didn’t become perfectly flat. There’s still a small residual increase of around 200 MB per hour, which is probably due to a few other smaller issues in other modules and not the same root cause as this one. **This wasn’t a magical "one fix cures all" patch. It just plugged the biggest hole. The remaining small tails still need to be shaved down one by one.**
- For this kind of "slow leak," a stress test script plus the memory curve is the most direct qualitative tool. If the curve rises in sync with the number of calls, you can usually narrow the suspect range down pretty quickly to "what resource isn’t being properly reused or closed."

One last note. Strictly speaking, the way this business logic is written isn’t really best practice. Throwing a slow, heavy LLM call directly into the web service’s own thread pool always comes with trade-offs. But the code had already been written this way and had been running in production for a long time, and there wasn’t a strong business reason to rewrite it. So for this fix, I deliberately set the principle to **zero changes to business logic**, and only worked on the layer of "how this logic gets executed," keeping both the scope of change and the risk as small as possible. And in practice, the result did meet expectations.

## Postscript

That said, if I were designing this from scratch, the better approach would be **not to run this kind of heavy task inside the web container at all**. Move it to offline machines, or process it with offline compute resources like Lambda. There are mainly two reasons:

- **Isolation**: this kind of heavy task that consumes both CPU and IO will naturally interfere with the web service if they share the same process. And the web service itself has much stricter requirements for stability and low latency, so the cost of interference is much higher. It’s far more cost-effective to let a less latency-sensitive offline task absorb that risk than to make the web service shake along with it.
- **Cost**: memory in web services is usually much more expensive than offline compute resources. This kind of heavy logic—loading model requests once, processing large objects—even if everything can eventually be reclaimed by GC, will still create memory spikes during execution. And if you’re even slightly careless (like this time), some of it may stay stuck in the heap forever and turn into a real leak. Putting this kind of high-memory operation on cheaper offline resources is simply the more economical architectural choice.