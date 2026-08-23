---
category: middleware
excerpt: 'The first thing I saw after being pulled into the incident chat was: "Every
  API is timing out." We stopped the bleeding first and gave the database a chance
  to recover, then circled back to figure out why a hidden risk planted two and a
  half days earlier would suddenly blow up all at once at that exact moment. Following
  the trail, it turned out to be a complete chain of events: an analytical query that
  had been left running, a high-traffic endpoint with a missing index, and a distributed
  lock that got released at exactly the wrong time. All three lined up and detonated
  together.'
keywords: postgresql, mvcc, autovacuum, 分布式锁, 索引, 数据库连接池, 生产事故, performance insights
lang: en
layout: post
title: A Database Avalanche Incident Investigation
---

## Introduction

I was busy with something else that day when I suddenly got pulled into an incident chat. The only message there was: **every single service endpoint is timing out like crazy**.

When you see a description like "timeouts across the board," the first instinct is: is this that old issue happening again? We had investigated a similar avalanche before, and the root cause back then was a call that was "written inside an async function but was actually doing synchronous blocking," which froze the event loop, dragged down health checks, and got the service marked unhealthy by the container orchestration platform, leading to traffic being drained and containers restarted. (I wrote up that full investigation separately, so I won’t repeat it here.) I started digging with that hypothesis in mind, but it turned out this time it was a completely different pitfall from start to finish. Still, once I kept digging, it pulled out more problems than I expected, and the chain was much longer too.

This post starts with mitigation, then moves on to the postmortem—because when something is on fire, what everyone wants to know first is always "how is it now?" The analysis can come after.

## 1. First, rule out "the old issue happening again"

Based on last time’s experience, the first step as usual was to check the service’s own basic metrics: CPU usage, memory pressure. Everything looked normal, with no unusual spikes at all.

Since what people were reporting was "all endpoints are timing out," what mattered more was really the latency of the core business APIs themselves. But since I suspected the old issue, the first thing I did was still to take a look at the health check endpoint’s TP95. If this was another event-loop-freeze situation, the health check would very likely be slowed down too, so it’s a very useful signal. This time, though, the health check TP95 was completely normal.

**Service-level metrics normal + health check normal**. Once those two were confirmed, I could basically rule out a recurrence of the same old problem. Since the application process itself looked healthy enough, the issue was probably not at the application layer. Time to look toward the middleware side.

## 2. Shift to middleware: the database CPU was already pinned

I immediately checked the database—and that’s when it became obvious something was seriously wrong. CPU had already **hit the ceiling**:

![数据库CPU飙升截图](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822181335361.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Database CPU usage during the incident window. Normally calm and uneventful, but here it went straight to 100%</center><br>

I quickly went to the AWS console hoping to see more detailed execution info, only to find that this database **didn’t have Performance Insights enabled**, so I couldn’t directly inspect historical Top SQL, wait event breakdowns, or other fine-grained data. Fortunately, the console still exposed some basic SQL latency stats. I glanced at the numbers and saw that **execution times were basically starting in the thousands of seconds**. That honestly startled me—I even wondered for a moment whether I had misread the unit or the dashboard was broken. Later I confirmed I hadn’t. That magnitude meant some statements had been stuck running inside the database for nearly an hour or even longer.

Without Performance Insights, fine-grained historical analysis was off the table. So the only option was the dumb but reliable one: connect directly with a DBA account and manually inspect the live state using system views like `pg_stat_activity`.

## 3. Digging through pg_stat_activity: two stuck culprits surfaced

```sql
SELECT pid, state, wait_event_type, wait_event, now() - query_start AS duration,
       left(query, 150) AS query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC
LIMIT 30;
```

Sorting by duration and scanning the list, two obvious culprits jumped out immediately:

**The first one**: a complex analytical query (cross-table aggregation, something like "count the distribution of dialogue rounds per game based on the event table"). Its state was `active`, and it had been **running continuously for more than two days**. It wasn’t just hanging there either—`wait_event_type` showed that it was genuinely burning CPU, and it even had two parallel worker processes attached. In other words, this was not some "forgotten idle transaction quietly lying around." It was a big CPU-hungry query that had been actively running for two and a half days, with parallelism enabled.

**The second one**: a batch of `UPDATE` statements with the same parameters but different PIDs, all targeting the same table. Their state was also `active`, and the wait events were all over the place—row locks, transaction locks, internal buffer locks. Their durations ranged from a few minutes to **nearly 5 hours**. At a glance, it was obvious this was the same scheduled job being triggered over and over again, piling up into a queue layer by layer—the oldest one had already blocked nearly 30 later arrivals.

At that point, the profiles of both culprits were pretty clear: one was continuously bleeding resources, the other was deadlocked into a queue, and both were the kind of thing where letting them continue was completely pointless.

## 4. Stop the bleeding first: kill them and let the database breathe

At an incident scene, the first rule is always mitigate first, investigate later. Once I confirmed these sessions were effectively stuck and there was no value in letting them continue, I cleared them out directly to free up resources. And this wasn’t just killing the two "representative" sessions mentioned above—I cleaned them up in batches by category:

```sql
-- First cancel the longest-running session in the analytical query chain;
-- the other parallel workers will terminate along with it
select pg_cancel_backend(<pid>);
```

- The analytical query itself plus its two parallel workers: **3 sessions** terminated together;
- The **32** queued `UPDATE` sessions in the lock chain: after confirming their durations and states one by one, I cleared them all, not just the head of the queue;
- There were also **738** sessions simultaneously running full table scans due to a missing index, all stuck on a leaderboard count query, and those were batch-cancelled as well.

After that, I watched the database metrics closely: CPU dropped immediately, active sessions plunged from several thousand down to a few dozen, and connection counts fell along with them. **A few minutes later**, timeout errors across all online endpoints had basically disappeared, and containers were no longer repeatedly failing health checks, getting restarted, and then drained again—the avalanche chain had been cut off at the root.

![QQ_1787441244261](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822182733778.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>(Placeholder image: after killing the two stuck session groups, active database sessions / CPU usage dropped sharply back to normal levels)</center><br>

One thing to make clear: this step was only mitigation. The two "lesions" were removed, but it answered none of the "why" questions—why that analytical query could run for two and a half days without anyone noticing, why a scheduled job that looked protected could still pile up nearly 30 concurrent executions, and so on. Those were the questions I only had time to go back and investigate after the fire was out.

## 5. Postmortem question one: why did it only blow up after two and a half days?

Working backward through the logs and timeline, the first question was: that analytical query had started running two and a half days earlier, so why did nothing happen for so long, and why did it blow up at this exact moment?

The answer had to do with the machine spec of this database instance. This box was pretty beefy (`db.m7i.8xlarge`): 32 vCPUs, 128 GB of memory, and high-performance storage. On a machine of that size, even with a heavy query continuously maxing out parallelism, it might not collapse the whole system in the short term. More often it just quietly consumes extra resources in the background, slows down cleanup tasks a bit, and causes subtle degradation that the business side barely notices.

![QQ_1787441341044](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822182904008.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Placeholder image: database instance spec screenshot, showing dozens of CPU cores / over 100 GB memory / high-performance storage)</center><br>

In other words, the database had actually **held on for more than 50 hours**. That analytical query kept bleeding resources in the background, garbage collection got slower, tables kept bloating day by day, but the machine had enough headroom to absorb it. Then, when the usual daily traffic peak arrived, the database—which had already lost a big chunk of its margin—finally couldn’t take it anymore, and everything broke at once. **That’s exactly what makes this kind of "chronic resource drain" issue so nasty: it doesn’t necessarily alert right away. Instead, it explodes the moment the remaining headroom is exhausted, making your first reaction "how did this happen with no warning?"—when in reality the warning signs were there the whole time, just masked by the machine’s spare capacity.** ![image-20260822182806103](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822182806142.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

## 6. Postmortem question two: how did the scheduled job’s row-lock avalanche build up?

The second culprit I killed during mitigation was backed by a very plain scheduled job: find records stuck in "creating" status for too long without updates, and mark them as failed once they time out. The code even had a Redis distributed lock specifically added to prevent multiple instances in the cluster from processing the same batch of data at the same time. (To avoid exposing the exact implementation, field names and variable names are replaced here, but the logic is the same.)

```python
LOCK_KEY = f"{env}:item:monitor_creating:lock"
LOCK_TIMEOUT = SCHEDULE_MIN_INTERVAL  # 300 seconds, same as the minimum scheduling interval

lock = redis_client.lock(LOCK_KEY, timeout=LOCK_TIMEOUT, blocking=False)
if not lock.acquire():
    return  # Lock is held, skip this round
try:
    # ... execute batch UPDATE ...
finally:
    lock.release()
```

At first glance, all the expected protections were there. So why did the live incident still end up with nearly 30 concurrent copies of the same `UPDATE`, with the longest one stuck for almost 5 hours? There were **two separate paths** here that could both make the lock expire too early, and the real problem was the combination of both:

1. **The TTL itself was too short**: the job was scheduled every 7.5 minutes, but the lock TTL was only 300 seconds (5 minutes). Once the database was already under heavy pressure and a single `UPDATE` execution stretched into hours, the lock would expire automatically before the job had actually finished—Redis neither knows nor cares whether the previous round is still running.
2. **When containers were drained and restarted, the lock was "gracefully" released early**: during the database overload, lots of containers were marked unhealthy by health checks because responses got too slow, and they were drained and restarted. If a container holding the lock while executing that `UPDATE` got terminated, the cleanup logic in `finally: lock.release()` would still run and actively release the lock—even if the database transaction it owned had not committed yet and was still holding a bunch of row locks. Once the lock was released, a newly started container could immediately acquire it and launch a **new round of the same `UPDATE` with the same conditions**, competing for locks on **the exact same rows** as the previous uncommitted transaction.

Both paths lead to the same bad state: "the lock looks free, but the underlying transaction is not actually done." So new rounds of the job kept pouring in one after another and queuing up, piling higher and higher. **In this kind of batch-processing scenario, "the lock has been released" should not be treated as equivalent to "it is now safe to start the next round." The semantics of the distributed lock need to cover whether the protected transaction has truly ended, not just whether the scheduler should launch another invocation.**

## 7. A side story: I thought it was an index issue, then EXPLAIN slapped me in the face

Since that `UPDATE` itself was taking hours, my first instinct was of course to suspect a bad index. I checked the table and the size was indeed scary: close to 800 GB and over 46 million rows. Then I checked how many rows actually matched the target status—only a bit over a hundred in the whole table. That number made me even more convinced it was an index problem. I guessed the existing index probably didn’t cover the time field, so even after narrowing down to those hundred-ish candidate rows, it still had to hit the table row by row to evaluate the timeout condition. On a nearly 800 GB table, that kind of random I/O could be brutal, and I was almost ready to recommend adding a composite index right away.

Luckily, before touching anything, I took one extra step and ran `EXPLAIN`. The result showed it was already using an index scan, with a cost so small it was basically negligible—the existing composite index had already filtered those hundred-ish rows cleanly. **There was nothing wrong with the execution plan of this statement itself**. Adding a new index had nothing to do with this incident. My earlier line of reasoning was simply wrong.

This detour is worth remembering: when you have **"the table is huge" + "very few rows match"** together, it’s extremely easy to instinctively blame indexing, but instinct is not a substitute for `EXPLAIN`. Fortunately, all I did was run one extra read-only verification step. I didn’t actually go and perform an unnecessary index change on a nearly 800 GB table—one that would also have consumed extra I/O. When the system is already under pressure, this kind of "trying to help but making it worse" can cost more than doing nothing.

## 8. Postmortem question three: where was the real load coming from?

If you only looked at that batch of lock-queued `UPDATE`s, it still didn’t explain why CPU had gone all the way to the ceiling. The reason they were stuck looked more like a consequence of "the whole instance is already under heavy pressure," not the cause of "these few statements brought down the whole instance."

It only became clear after comparing several load metrics: active sessions suddenly shot up to **2000+**, and peak load briefly reached **2332**—while the safe baseline for a 32-core instance under normal conditions is only around 32. That means it was overloaded by **more than 70x**. At the same time, total database connections were approaching **2700**. The real load hog was a very unremarkable count query on another table:

```sql
SELECT count(*) FROM t_item_result WHERE game_id = $1 AND public IS true;
```

This query backed a leaderboard-style endpoint. The existing index on that underlying table did not have `game_id` as its leading column, so filtering by `game_id` couldn’t use it effectively. Under normal low traffic, that was tolerable. But when the traffic peak hit that day, hundreds of concurrent requests all landed on it at once, and every single one became a full table scan. CPU got burned through immediately. At the time, there were nearly 500 queries running longer than 60 seconds. Of those, only about one-third were related to the earlier version table; **the remaining two-thirds were innocent queries dragged down by this environment**. That ratio also confirmed that the main load source was not the `UPDATE` path. There was also another comment-related table where a join field lacked proper index support, which added fuel to the fire too, though not at the same scale as this count query.

## 9. Making it worse: even the last self-healing path was blocked

In theory, when the database gets into this kind of bloat and backlog, there’s still one last line of defense: `autovacuum`, which can slowly clean things up and let the system recover on its own. But when I checked the live state, even that escape route was blocked. The `autovacuum` process responsible for cleaning a large-field storage area had been stuck for **3 hours and 7 minutes** without finishing. Meanwhile, `autovacuum` on two other core tables had also been slowed by throttling for **12 minutes 49 seconds** and **6 minutes 1 second**, unable to make normal progress.

The fact that three different `autovacuum` processes were each stuck on different tables showed this wasn’t a localized issue on one table. The entire instance was so resource-constrained that even background cleanup tasks could no longer get enough execution time slices—**at that point self-healing was completely impossible, and only manual intervention could stop the bleeding**, which is exactly what I described earlier in section 4.

## 10. Putting the full chain together

If you connect the answers to the earlier questions, the escalation path looks roughly like this:

1. Two and a half days earlier, an analytical query with parallelism started running continuously and never exited. It not only consumed resources by itself, but because the transaction stayed open for so long, it also held back the global MVCC snapshot horizon, preventing `autovacuum` from properly cleaning dead tuples and causing core tables to keep bloating.
2. The database was provisioned generously enough that it held on for more than 50 hours without obvious symptoms. Then a routine traffic peak arrived, and a hot count query missing the right index got amplified by concurrency into a large number of full table scans, instantly burning through CPU.
3. In that CPU-overloaded environment, a scheduled job that was originally protected by a distributed lock started queueing up round after round of the same `UPDATE`, because the TTL was too short and the lock was also being released early when containers were drained and restarted. It piled up to nearly 30 sessions.
4. Nowhere in the whole chain was there any statement-level timeout configured. So large numbers of requests could only wait indefinitely, until the containers serving them were themselves marked unhealthy by health checks and drained/restarted, at which point the coroutines were passively cancelled. Containers got replaced in waves—two waves in total, adding up to more than a dozen containers being marked unhealthy and restarted due to probe timeouts—which in turn handed another knife to step 3: new containers came up, immediately acquired the newly released lock, and launched another round of conflicting `UPDATE`s, amplifying the loop.
5. By then, the self-healing mechanism (`autovacuum`) had already been dragged down to the point of uselessness, so only manual intervention could stop the damage.

With all five stacked together, the database and every service depending on it slowed down across the board. From the business side, the direct symptom was simply "all endpoints are timing out." And once those two root sources were killed, the chain snapped immediately and all metrics quickly returned to normal.

## 11. The real holes that need fixing

What we did on-site was just stopping the bleeding. It didn’t solve any root cause. After sorting things out, there are quite a few fixes to make. Roughly in priority order:

**1. Add statement-level timeouts to database connections**

I checked and found that at the database connection layer, there is currently no statement-level timeout configured at all (`statement_timeout` in PostgreSQL). That means how long a SQL statement can stay stuck in the database depends entirely on which outer layer times out first. If you don’t set this, you’re basically giving every slow query an unlimited tab.

The setup is simple. PostgreSQL supports several levels, so pick what fits:

```sql
-- Option 1: session-level, run once after the connection is established;
-- only affects the current connection
SET statement_timeout = '15s';

-- Option 2: per database role; automatically applies to all future connections for that user
ALTER ROLE app_user SET statement_timeout = '15s';

-- Option 3: instance-level default (in postgresql.conf or a cloud provider parameter group)
statement_timeout = 15000   -- unit is milliseconds
```

If you’re using a connection pool / ORM, it’s even better to pass it in when creating connections, for example in Python `asyncpg`:

```python
create_async_engine(
    DATABASE_URL,
    connect_args={"server_settings": {"statement_timeout": "15000"}},  # milliseconds
)
```

The exact timeout value can’t just be guessed. It needs to be tiered by endpoint type: user-facing core read APIs usually get single-digit to low double-digit seconds; background batch jobs and offline tasks can be looser, maybe tens of seconds. But **no matter which tier, it must be an explicit number, not "unset."** In this incident, the longest batch of queries was stuck for nearly 5 hours. If even the loosest tier had been set to something like 60 seconds, it never would have dragged on to the point where manual intervention was required.

**2. Change the scheduled job to commit in batches; the distributed lock can’t rely on a fixed TTL alone**

The table is still growing, and the one-shot large batch `UPDATE` approach itself does not age well as data volume increases. It should be split into smaller chunks with batched commits. On the distributed lock side, having a TTL that doesn’t cover "how long the job might take in the worst case" is already a hidden risk, and the lock release timing needs to be redesigned too. A passive service restart should not be treated as equivalent to "it is now safe to release the lock and wake the next round." Either add a renewal mechanism, or bind the lock lifecycle much more tightly to the state of the transaction it protects.

**3. Add the two indexes that are actually missing**

Add an index on the table hit by the hot count query that truly covers the real query conditions, using a non-blocking index build method. Also add the corresponding index for the field used by the comment-related join query. This incident was also a reminder to myself: during investigation, don’t decide by instinct which table "should get an index." Use `EXPLAIN` or historical load analysis tools first to identify the real load source, then make changes.

**4. Add caching or periodic pre-aggregation for the hot count endpoint**, instead of doing a real-time `count(*)` every time, to reduce direct pressure on the underlying large table.

**5. Add a read replica dedicated to offline analysis**: even just having a read-only instance that doesn’t serve online business traffic, and using it specifically for offline analysis and data verification queries, would help avoid situations like "someone forgets to close an analytical script connection and drags down the production primary database." Using the primary everywhere for ad hoc analysis creates way too much risk exposure.

**6. Fill in the missing key monitoring and alerts**: core database load metrics, slow SQL distribution, and so on. This incident also confirmed one thing along the way—tools like Performance Insights that let you inspect historical Top SQL and wait events do cost a bit, but the difference between being able to locate the root cause in a few minutes during an incident versus not being able to is huge. For core databases, it’s worth enabling them as a standard practice.

## Summary

My biggest takeaway from this investigation is: **production incidents are rarely caused by a single factor. Most of the time, they’re several individually non-fatal little problems that happen to line up at the same moment.** A forgotten analytical script, a hot endpoint missing an index, a distributed lock with a TTL set too short and released at the wrong time, plus no statement-level timeout anywhere in the chain—look at them one by one and each is the kind of oversight people are usually willing to forgive. Stack them together, and you get a real avalanche. And because the machine itself had strong enough performance, the problem stayed latent for more than 50 hours before a traffic peak finally detonated it. That kind of "delayed explosion" is even more dangerous than "immediate alerting."

Another more concrete lesson is this: **during troubleshooting, even inferences that "look perfectly reasonable" are worth validating with tools before you act.** At one point I was convinced it was an index issue. If I hadn’t run that extra `EXPLAIN`, I might have made a completely unnecessary index change on a nearly 800 GB table—one that would also have consumed extra I/O. Looking at a blocking chain can tell you who is waiting on whom, but finding the real load source always comes back to one question: "who is actually burning CPU?" The two are not interchangeable. And when an incident happens, stopping the bleeding and giving the system room to breathe is always more important than trying to analyze everything slowly while the pressure is still on.