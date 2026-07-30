---
category: middleware
excerpt: Both the web service and message production were fine—only the consumer would
  quietly exit after hitting a single business exception. In the end, I found out
  what actually killed the task wasn’t the business logic at all, but a single error
  log line.
keywords: python, sqs, loguru, asyncio, debugging
lang: en
layout: post
title: 'Troubleshooting a Silent Exit in an SQS Consumer: Turns Out the Root Cause
  Was in the Logs'
---

## Preface

A while back I ran into a really weird issue: an async settlement job had clearly been successfully sent to SQS, but it just wouldn’t get consumed. At first I thought it was just some delivery delay, but when I checked the queue, I found dozens of messages piled up—and none of them were in an “in-flight” state.

Even stranger, the FastAPI service itself was totally fine: health checks were good, the API was being called constantly, and the SNS logs responsible for publishing messages kept printing. In other words, **the producer was alive, the web service was alive, and only the consumer quietly disappeared.**

This SQS consumer wasn’t a separate process—it was a background asyncio Task created when FastAPI started. After restarting the service, the backlog would start getting consumed again. It looked like some particular message handling run killed the poller. But there was no process crash in the logs, no obvious uncaught exception—everything about it felt off.

I took quite a few detours during this investigation. At different points I suspected SQS network calls hanging, database session rollbacks, thread pool deadlocks, and I even doubted Python’s `for` loop exception boundaries. In the end, after a bunch of controlled comparisons, I discovered what actually killed the consumer wasn’t the original business exception—it was **the single log line that recorded that exception**.

## First, confirm where the messages actually went

I first noticed the problem because one async settlement record got stuck in an in-between state: “business already completed, but async result not written back yet.”

The normal flow is roughly:

```text
User request
  ↓
Persist business state
  ↓
Send async settlement event
  ↓
SQS consumer pulls message
  ↓
Execute settlement and write back result
```

This record showed the first half completed, but the second half never finished. My first instinct was: did I turn off the MQ switch locally for testing, and somehow it never got enabled in the dev environment?

But after checking the config and producer logs, I ruled that out quickly. The publish logs were complete, SNS returned a message ID, so the message was definitely published successfully. Then I checked SQS: the queue had lots of visible messages, but none were being processed by a consumer.

Next I stitched together logs from the same container in time order, and a key pattern emerged:

- HTTP requests were normal the whole time;
- health checks were normal the whole time;
- SNS kept publishing events during that period;
- the SQS poller stopped printing “received message” after handling one failed message;
- only after the next service restart did the poller print its startup logs again.

That basically confirmed it: **the whole service wasn’t down, and messages weren’t failing to publish—only the SQS poller Task inside the process was gone.**

## First suspicion: was an exception not being caught?

At the time, the last consumer log was a business exception like “settlement record not found.” So my first reaction was to inspect the consumer’s exception handling.

The redacted structure looked like this:

```python
async def run_poller():
    while not stop_event.is_set():
        try:
            messages = await receive_messages()
        except Exception as exc:
            logger.error("Receive message failed: {}", exc)
            continue

        for message in messages:
            try:
                await process_message(message)
            except Exception as exc:
                logger.error(
                    f"Unexpected error processing message: {exc}",
                    exc_info=True,
                )
```

At first I suspected we were missing another `try/except` outside `for message in messages`. If something outside single-message processing threw, it could break out of the whole `while` loop.

But thinking it through, that didn’t hold up. Each message already had its own `try/except`, and between iterations it’s just a plain Python list traversal—no business logic, no I/O. You can’t just blame the loop because you “should catch one more layer.”

Also, the failed message had already printed a full business exception stack trace, which meant the original exception really was caught by the exception handling inside `_process_message()`. The real problem had to be happening after it was caught.

So I parked this line of thought.

## Second suspicion: was the SQS request hanging?

There was one difference between the success path and the failure path: on success we delete the message; on failure (to retry) we call `change_message_visibility` to adjust the message visibility timeout.

Those boto3 calls are synchronous, so the code used `run_in_executor()` to throw them into a thread pool:

```python
await loop.run_in_executor(
    None,
    change_message_visibility,
    receipt_handle,
    retry_delay,
)
```

So the second guess was: could it be that after a failure, `change_message_visibility` got stuck on a network connection, causing the poller to await forever?

This explanation looked very plausible for a while:

- only the failure path calls it;
- the poller getting stuck wouldn’t affect other FastAPI Tasks;
- the HTTP service staying normal matched the symptoms perfectly;
- after restart, connections get rebuilt and the consumer recovers.

I even considered configuring boto3 `connect_timeout` / `read_timeout`, and wrapping it with `asyncio.wait_for()`.

But I still lacked direct evidence. `run_in_executor()` won’t block the whole event loop, but “not blocking the event loop” and “not blocking the current poller Task” are two different things. Even if the thread pool function never returns, the poller will still wait forever on that `await`.

It was theoretically consistent, but I couldn’t prove it was actually stuck there. Continuing to guess would just be bouncing between different “reasonable stories.”

So I stopped guessing and started adding trace logs to reproduce it in a controlled way.

## Stop guessing, start doing controlled comparisons

I added numbered trace logs at every key point in the message consumption path:

```text
T1  Business handling exception caught
T2  About to write failure status
T3  Failure status commit done
T4  process_message caught exception
T5  Compute retry interval
T6  Release distributed lock
T7  Lock released
T8  Enter retry branch after failure
T9  About to change message visibility
T10 Visibility change done
T11 About to re-raise original exception
T12 Original exception raised to poller
T13 Poller outermost catch caught exception
```

Then I started crafting different types of failing messages.

### A normal ValueError

First I sent an event with no registered handler, so dispatch would directly throw a plain `ValueError`. The whole chain went from T1 to T13, and then the poller continued into the next `receive_message` loop—completely normal.

### Invalid UUID

Next I passed a malformed UUID so the Python standard library would throw:

```text
ValueError: badly formed hexadecimal UUID string
```

Still normal. The message retried a few times, and each time the poller cleanly went through T1 to T13 and then continued the next loop.

### Throwing inside a DB context

Then I crafted a scenario closer to real business logic: open an async DB session, run a query so a transaction is actually established, and then throw an exception inside the session context.

This was mainly to verify whether rollback/close during session exit could hang the failure path. The result was still normal: DB context exit, failure status commit, message visibility change, re-raise—everything completed.

At this point, network hangs, DB rollbacks, and the consumer’s exception structure were all looking less and less like the root cause.

### Switching to the real business exception

Finally I swapped the exception to the kind used in the real business flow—an exception carrying error details (with business names/data replaced by generic examples):

```python
class SettlementConflictError(Exception):
    def __init__(self, message: str):
        detail = {
            "type": "settlement_conflict",
            "message": message,
            "retryable": True,
        }
        super().__init__(detail)
```

This time, the issue reproduced reliably.

The logs reached T13, meaning the poller outer layer successfully caught the original business exception. But the error log that should have printed immediately after T13 didn’t appear, and the next poller heartbeat never showed up.

Meanwhile, another independent background Task was still printing logs normally, and HTTP requests were fine. So the process and event loop weren’t dead—**only the SQS poller Task exited on the line right after T13.**

After T13 there was no `await`, just a single log line:

```python
logger.error(
    f"Unexpected error processing message: {exc}",
    exc_info=True,
)
```

The scope finally shrank from an entire MQ/DB/async call chain down to one log statement.

## The problem ended up being a single log line

To verify whether logging itself was the issue, I ran a few small experiments:

```python
print("before logger.error")

logger.error("static message")

logger.error(f"Unexpected error processing message: {exc}")

print("after logger.error")
```

After removing `exc_info=True` entirely, the consumer could continue the next loop normally.

There was also a very misleading detail: at first I only changed it to `exc_info=False`, and the consumer still died. It’s easy to conclude “if False still kills it, then it’s not `exc_info`.”

In reality, Loguru doesn’t care whether that value is `True` or `False`. What matters is: **you passed an extra keyword argument at all**. As long as `kwargs` is non-empty, it triggers message template formatting.

That also finally explained the real difference:

| Exception | Result of `str(exc)` | Reproduces? |
|---|---|---|
| plain `ValueError` | `badly formed hexadecimal UUID string` | No |
| business exception | `{'type': 'settlement_conflict', ...}` | Yes |

Both exceptions were caught fine. The difference wasn’t inheritance, and it wasn’t the DB context—it was **whether the string form contained curly braces**.

## The real root cause: Loguru formatted it again

`exc_info=True` is a Python standard library `logging` pattern, used to include the current exception traceback:

```python
import logging

try:
    do_something()
except Exception:
    logging.getLogger(__name__).error(
        "Something failed",
        exc_info=True,
    )
```

But this project used the third-party logging library Loguru. In Loguru, printing the current exception should be done with:

```python
logger.exception("Something failed")
```

or:

```python
logger.opt(exception=True).error("Something failed")
```

Loguru’s `error()` treats extra positional/keyword arguments as formatting parameters for the message template. You can roughly think of its internal logic as:

```python
def error(message, *args, **kwargs):
    if args or kwargs:
        message = message.format(*args, **kwargs)
    write_log(message)
```

Now back to the problematic code:

```python
logger.error(
    f"Unexpected error processing message: {exc}",
    exc_info=True,
)
```

First, the f-string is evaluated. The business exception’s `str(exc)` is the string form of a Python dict, so the final message passed to Loguru becomes:

```text
Unexpected error processing message:
{'type': 'settlement_conflict', 'message': 'record not found', 'retryable': True}
```

Note: this is not JSON—it’s Python `dict` string representation. It has single quotes, `True`, and most importantly, it has curly braces.

Then Loguru sees the extra `exc_info=True`, so it formats the already-built message again:

```python
message.format(exc_info=True)
```

Python’s `str.format()` treats curly braces as placeholders. So `{'type': ...}` is no longer plain text—it’s interpreted as a field to substitute. Of course there’s no matching parameter for it, so it throws a new `KeyError`.

So the full exception chain is actually:

```text
Settlement job throws SettlementConflictError
  ↓
Business exception is caught normally; failure status and retry time are written normally
  ↓
Original exception is re-raised to the poller outer layer
  ↓
Poller outer catch catches it again and tries to log an error
  ↓
Loguru runs str.format() on a message containing curly braces
  ↓
Logging code throws a new KeyError
  ↓
New exception escapes the while loop; poller Task ends
```

In other words, **the original business exception was handled correctly from start to finish. What wasn’t handled was the second exception created inside the exception-handling code.**

This also explains why the invalid UUID case didn’t reproduce. Its error message is plain text with no curly braces. Even if Loguru runs `.format(exc_info=True)` again, there are no placeholders, so the string comes back unchanged and everything looks fine.

The most insidious part of this bug is exactly that: the same error log line had been running for a long time, and most exceptions were fine. Only when a particular exception’s string happened to include curly braces would it suddenly kill the consumer.

## Why the whole service didn’t crash, but the consumer silently exited

This also involves an easy-to-confuse asyncio concept: **a coroutine function is not the same thing as an independent Task.**

The consumer was started roughly like:

```python
poller_task = asyncio.create_task(run_poller())
```

That creates an independent poller Task. But later:

```python
await process_message(message)
await dispatch(event)
await handle_settlement(payload)
```

These `await`s do not automatically create new Tasks at each layer. They all run sequentially inside that original `poller_task`, just with a deeper call stack.

So when the `KeyError` thrown by the outermost error log escapes `run_poller()`, only that poller Task ends. FastAPI’s HTTP request Tasks, health checks, and other background tasks are still alive, so the container naturally won’t exit.

From the outside, you get a very confusing state:

```text
Container: Running
Health check: 200
API requests: normal
Message production: normal
SQS queue: continuously piling up
Consumer: already dead
```

Then why didn’t we even see the common:

```text
Task exception was never retrieved
```

asyncio usually prints that when a Task finishes with an exception, nobody retrieves its result, and the Task object gets garbage-collected—via the event loop’s exception handler. But our lifespan code kept a reference to `poller_task`, planning to cancel and await it during shutdown.

The Task had already finished, but the object wasn’t collected, so that fallback warning didn’t show up promptly. Without a restart, it could sit in the state of “Task is dead, but the reference is still alive” for a long time.

That’s why this outage looked so quiet.

## Fix

The direct fix is simple: replace the standard library `logging` style with Loguru’s own API:

```python
try:
    await process_message(message)
except Exception:
    logger.exception("Unexpected error processing message")
```

`logger.exception()` automatically includes the current traceback, so there’s no need to pass `exc_info=True`.

If you still want to include the exception object as part of the message, you can use Loguru’s own placeholder style:

```python
try:
    await process_message(message)
except Exception as exc:
    logger.exception(
        "Unexpected error processing message: {}",
        exc,
    )
```

Here the template string is fully under our control, with exactly one `{}`. After `exc` is inserted, any curly braces inside its string won’t be recursively parsed again, so it’s safe.

After finding this, I scanned the whole project. This kind of misuse isn’t necessarily limited to the consumer—anywhere that satisfies both conditions can hit it:

1. Using Loguru, but passing standard library `logging`’s `exc_info=`;
2. The final log message contains unescaped curly braces.

So the fix can’t be just changing the one line at the incident site. A safer approach is:

- Search the whole repo for `exc_info=` in Loguru calls;
- In `except` blocks, standardize on `logger.exception()`;
- When you need finer control, use `logger.opt(exception=True)`;
- Don’t “fix” places that truly use standard library `logging`—it legitimately supports `exc_info=True`.

I also added a regression test. The key isn’t testing a specific business error, but constructing **an exception whose string contains curly braces**, making the first message fail, and then confirming the consumer can still process the second message:

```python
class BraceError(Exception):
    pass


async def test_poller_survives_brace_error():
    messages = [
        BraceError({"type": "conflict"}),
        "next-message",
    ]

    processed = await run_test_poller(messages)

    assert "next-message" in processed
```

That way, even if someone copies the standard-library logging pattern back in, the test will catch it immediately.

Finally, long-running background Tasks should ideally have a bit of liveness monitoring. For example, add a done callback:

```python
def report_task_exit(task: asyncio.Task) -> None:
    if task.cancelled():
        return

    error = task.exception()
    if error is not None:
        logger.error("SQS poller exited unexpectedly: {}", error)


poller_task = asyncio.create_task(run_poller())
poller_task.add_done_callback(report_task_exit)
```

More fully, you can use a supervisor to alert or restart the consumer after an unexpected exit. But note: auto-restart should only be an availability backstop, not a substitute for fixing the root cause. Otherwise the Task will crash and respawn repeatedly—you’ve just turned “silent death” into “silent restart.”

## Afterword

After this investigation, the biggest takeaway for me is: **an explanation sounding reasonable is not the same thing as having evidence.**

Network hangs, DB rollbacks, thread pool blocking—each of these could explain part of the symptoms, and each sounds plausible. If I had acted on one guess and added timeouts/retries, the consumer might have looked stable for a while, but the real issue would still be buried in the logging code, and it would still blow up the next time an exception with curly braces showed up.

What actually made the problem converge wasn’t reading tons more code—it was continuously narrowing variables:

- Do normal exceptions work?
- Does a DB context change the outcome?
- What happens if I swap the exception type on the same call chain?
- What’s the exact difference after converting the two exceptions to strings?
- What is the last line of code the poller successfully executes?

Step by step, the problem shrank from “why does the SQS consumer die” to “why does this Loguru line throw `KeyError`,” and the difficulty dropped dramatically.

I also used to think logs were just side-channel code: if logging fails, worst case you lose a log line—it shouldn’t affect the business. This incident was a good reset: **logging is on the real execution path. As long as it’s a synchronous call, it can absolutely throw exceptions, change control flow, and even kill a long-running consumer.**

Sometimes the truly dangerous thing isn’t the original exception, but the new exception we accidentally create while handling it.