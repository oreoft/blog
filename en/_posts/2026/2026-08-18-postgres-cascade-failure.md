---
category: middleware
excerpt: 'The first thing I saw after being pulled into the incident chat was: "Every
  API is timing out." The immediate priority was to stop the bleeding and give the
  database a chance to recover. Only then could we circle back and figure out why
  a hidden risk planted two and a half days earlier had suddenly blown up all at once
  at this exact moment.


  Following the trail, it turned out to be a complete chain of three things coming
  together: an analytical query that had been left running, a hot endpoint missing
  an index, and a distributed lock that got released at exactly the wrong time.'
keywords: postgresql, mvcc, autovacuum, 分布式锁, 索引, 数据库连接池, 生产事故, performance insights
lang: en
layout: post
title: A Database Avalanche Incident Investigation
---

## Preface

That day I was busy with something else when I suddenly got pulled into an incident chat. The only message was one line: **every single service endpoint is timing out like crazy**.

When you see a description like "timeouts across the board," the first instinct is: is this that old issue happening again? We had investigated a similar avalanche before, and the root cause back then was a call that was "written inside an async function but was actually synchronously blocking," freezing the event loop and then dragging down health checks, which caused the container orchestration platform to mark instances unhealthy, remove traffic, and restart them. (I wrote up the full investigation of that one in a separate post, so I won’t repeat it here.) I started digging with that assumption in mind, but this time it turned out to be a completely different pit from start to finish. Still, once I kept digging, it pulled out more problems than I expected, and the chain was much longer too.

This post starts with damage control, then moves on to the retrospective—because when something breaks, what everyone wants to know first is always "how is it now," and the analysis can come later.

## 1. First, rule out the possibility of "the old problem happening again"

Based on last time’s experience, the first step as usual was to check the service’s own basic metrics: CPU usage, memory pressure. Everything looked normal, with no abnormal spikes at all.

Since what people were reporting was "all endpoints are timing out," what mattered more was really the latency of the core business endpoints themselves. But since I suspected the old issue, the first thing I still did was take a look at the TP95 of the health check endpoint—if this was another event-loop-freeze situation, the health check would very likely be slowed down too, which makes it a very useful signal. This time, though, the health check TP95 was completely normal.

**Basic service metrics normal + health check normal**—once those two were confirmed, I could basically rule out a recurrence of the same old issue. Since the application process itself looked healthy, the problem was probably not in the application layer. Time to look toward the middleware layer.

## 2. Shift to middleware: database CPU was already maxed out

I immediately checked the database—and one look was enough to tell something was seriously wrong. CPU had already **hit the ceiling**:

![Database CPU spike screenshot](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822181335361.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Database CPU usage during the incident window. Usually calm and flat, but here it went straight to 100%</center><br>

I quickly went to the AWS console hoping to see more detailed execution info, only to find that this database **did not have Performance Insights enabled**, so I couldn’t directly inspect historical Top SQL, wait event distribution, or other fine-grained data. Fortunately, the console still exposed some basic SQL latency stats. I glanced at the numbers—and **the durations were basically all in the thousands of seconds**, which honestly startled me. For a moment I even wondered whether I had misread the unit or whether the dashboard was broken. Later I confirmed I hadn’t misread it. At that scale, some statements had already been stuck running in the database for close to an hour, or even longer.

Without Performance Insights, fine-grained historical analysis was off the table. So I had to fall back to the dumb method: connect directly with a DBA account and manually inspect the live state using system views like `pg_stat_activity`.

## 3. Dig directly into pg_stat_activity: two deadlocked offenders surfaced

```sql
SELECT pid, state, wait_event_type, wait_event, now() - query_start AS duration,
       left(query, 150) AS query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC
LIMIT 30;
```

Sorting by duration and scanning the results, two obvious offenders jumped out immediately:

**The first one**: a complex analytical query (cross-table aggregate statistics, something like "count the distribution of dialogue rounds per game from the event table"). Its state was `active`, and it had been **running continuously for more than two days**. It wasn’t just hanging there either—`wait_event_type` showed that it was genuinely burning CPU, and it even had two parallel worker processes attached. In other words, this was not some "forgotten idle transaction quietly lying around." It was a large query that had been actively consuming CPU for two and a half days, with parallelism enabled.

**The second one**: a batch of `UPDATE` statements with identical parameters and only different PIDs, all targeting the same table. Their state was also `active`, and the wait events were all over the place—row locks, transaction locks, internal buffer locks. Their durations ranged from several minutes to **nearly 5 hours**. At a glance, it was obvious this was the same scheduled job being triggered over and over, piling up into a queue layer by layer—the oldest one had already blocked nearly 30 later arrivals.

At that point the profiles of both offenders were pretty clear: one was continuously bleeding the system dry, and the other was deadlocked in a queue. And both were the kind where letting them continue was completely pointless.

## 4. Stop the bleeding first: kill them and let the database breathe

At an incident site, the first principle is always stop the bleeding before investigating the cause. Once I confirmed these sessions were effectively stuck and there was no value in letting them continue, I cleared them directly to free up resources. This wasn’t just killing the two "representatives" mentioned above—I cleaned them up in batches by category:

```sql
-- First cancel the longest-running session in that analytical query chain;
-- the other parallel workers will terminate along with it
select pg_cancel_backend(<pid>);
```

- The analytical query itself plus its two parallel workers: **3 sessions** terminated together;
- The **32** queued `UPDATE` sessions in the lock chain: after confirming their durations and states one by one, I cleared all of them, not just the head of the queue;
- Sessions stuck on leaderboard count queries due to missing indexes and doing full table scans: there were **738** of them running at the time, and I batch-canceled those too.

After that, I watched the database metrics closely: CPU dropped immediately, active sessions fell from several thousand down to a few dozen, and connection count dropped along with them. **A few minutes later**, timeout errors across all online endpoints had basically disappeared, and containers were no longer repeatedly being marked unhealthy by health checks, restarted, and removed from traffic—the avalanche chain had been cut off at the root.

![QQ_1787441244261](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822182733778.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>(Placeholder image: after killing the two stuck session groups, database active sessions / CPU usage dropped sharply back to normal levels)</center><br>

One thing to make clear: this step was only damage control. The two "lesions" were removed, but it answered none of the "why" questions—why that analytical query could run for two and a half days without anyone noticing, why a scheduled job that looked protected could still pile up nearly 30 concurrent runs, and so on. Those were the things I only had time to investigate after the system was stabilized.

## 5. Retrospective question one: why did it only blow up after two and a half days?

Tracing backward through logs and the incident timeline, the first question was: that analytical query had clearly started two and a half days earlier, so why did nothing happen for so long, and why did it collapse at this exact moment?

The answer had to do with the machine spec of this database. This instance was quite beefy (`db.m7i.8xlarge`): 32 vCPUs, 128 GB memory, and high-performance storage. On a machine of that size, even with one heavy query continuously running at full parallelism, it might not be enough to crush the system outright in the short term. More often it just "quietly consumes more resources" and "slows background cleanup tasks a bit" in ways that aren’t very obvious, while the business side barely notices.

![QQ_1787441341044](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822182904008.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>(Placeholder image: database instance spec screenshot, dozens of CPU cores / over 100 GB memory / high-performance storage)</center><br>

In other words, the database had actually **been brute-forcing its way through for more than 50 hours**. That analytical query had been bleeding resources in the background the whole time, garbage collection had been slowed down, and tables had been bloating day by day—but the machine had enough headroom to survive it. It wasn’t until the day’s normal traffic peak arrived that the database, which had already lost a big chunk of its margin, finally couldn’t take it anymore, and the problem exploded all at once. **That’s exactly what makes this kind of "chronic resource drain" issue so nasty: it doesn’t alert immediately. Instead, it suddenly blows up at the moment the remaining headroom is exhausted, making your first reaction "how did this happen with no warning?"—when in reality the warning signs were there the whole time, just masked by the machine’s excess capacity.** ![image-20260822182806103](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822182806142.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

## 6. Retrospective question two: how did the scheduled job’s row-lock avalanche build up?

The second offender I killed during damage control came from a very plain scheduled job: find records stuck in "creating" status for too long without updates, and mark them as failed once they time out. The code explicitly used a Redis distributed lock to prevent multiple instances in the cluster from processing the same batch of data at the same time. (To avoid exposing the exact implementation, field names and variable names have been replaced, but the logic is unchanged.)

```python
LOCK_KEY = f"{env}:item:monitor_creating:lock"
LOCK_TIMEOUT = SCHEDULE_MIN_INTERVAL  # 300 seconds, same as the minimum scheduling interval

lock = redis_client.lock(LOCK_KEY, timeout=LOCK_TIMEOUT, blocking=False)
if not lock.acquire():
    return  # Lock is occupied, skip this round
try:
    # ... execute batch UPDATE ...
finally:
    lock.release()
```

At first glance, all the expected protections seemed to be there. So why did the live incident still end up with nearly 30 concurrent copies of the same `UPDATE`, with the longest one stuck for almost 5 hours? There were **two separate paths** here that could both make the lock expire too early, and the real problem was the combination of both:

1. **The TTL itself was too short**: the job ran every 7.5 minutes, but the lock TTL was only 300 seconds (5 minutes). Once the database was already under heavy pressure and a single execution of this `UPDATE` got dragged out to several hours, the lock would automatically expire before the job had actually finished—Redis neither knows nor cares whether the previous round is still executing.
2. **When a container was removed from traffic and restarted, the lock was "gracefully" released early**: during database overload, lots of containers were marked timed out by health checks because responses got too slow, and were then removed and restarted. If a container holding the lock while executing this `UPDATE` got taken down, the cleanup logic in `finally: lock.release()` would still run, actively releasing the lock—even if the database transaction it was responsible for had not committed yet and was still holding a bunch of row locks. Once the lock was released, a newly started container could immediately acquire it and launch **another round of the same `UPDATE` with the same conditions**, competing for locks on **the exact same rows** with the previous transaction that still hadn’t committed.

Both paths lead to the same situation: **the lock looks free, but the underlying transaction is not actually done**. So new rounds of the job keep pouring in and queueing up, one after another, piling higher and higher. **In this kind of batch-processing scenario, "the lock has been released" should not be treated as equivalent to "it is now safe to start the next round." The semantics of the distributed lock need to cover whether the transaction it protects has truly ended, not just whether the scheduler layer should launch another invocation.**

## 7. Side note: I thought it was an index issue, and then EXPLAIN slapped me in the face

Since this `UPDATE` itself was taking hours to run, my first instinct was of course to suspect a bad or missing index. I checked the table and the size was indeed scary: nearly 800 GB and more than 46 million rows. Then I checked how many rows matched the target status—only a little over a hundred in the whole table. That number actually made me even more convinced it was an index problem. I guessed the existing index didn’t cover the time field, so even after narrowing down to those hundred-odd candidate rows, it still had to fetch rows one by one to evaluate the timeout condition, and on a nearly 800 GB table that random I/O could be very expensive. I was almost ready to recommend adding a composite index on the spot.

Fortunately, before touching anything, I took one extra step and ran `EXPLAIN`. The result showed it was already using an index scan, and the cost was negligible—an existing composite index had already filtered those hundred-odd rows very cleanly. **There was nothing wrong with the execution plan of this statement itself**. Adding a new index had nothing to do with this incident; my earlier line of reasoning was simply wrong.

This side note is worth remembering: **when you have "the table is huge" + "very few rows match," it’s extremely easy to instinctively suspect indexing, but instinct is not a substitute for `EXPLAIN`.** Luckily, all I did was run one extra read-only verification step. I didn’t actually go and perform an unnecessary index change on a nearly 800 GB table—which would also have consumed extra I/O. When the system is already under pressure, this kind of "trying to help but making it worse" can cost more than doing nothing.

## 8. Retrospective question three: where was the real load coming from?

If you only looked at that batch of lock-queued `UPDATE`s, it still didn’t explain why CPU had hit the ceiling. The reason they were stuck looked more like a consequence of "the whole instance is already under heavy pressure," not the cause of "these few statements dragged the whole instance down."

Only after comparing several load metrics did the picture become clear: active sessions spiked instantly to **2000+**, and peak load briefly reached **2332**—while the safe baseline for this 32-core instance under normal conditions was only around 32, meaning it was overloaded by **more than 70x**. At the same time, total database connections approached **2700**. The real load hog was a very unremarkable count query on another table:

```sql
SELECT count(*) FROM t_item_result WHERE game_id = $1 AND public IS true;
```

This query backed a leaderboard-style endpoint. The existing index on the underlying table did not have `game_id` as its leading column, so filtering by `game_id` couldn’t use it effectively. Under normal low traffic, that was tolerable. But when the day’s traffic peak hit, hundreds of concurrent requests all landed on it at once, and every single one became a full table scan, instantly burning CPU to the ground. At the time, there were nearly 500 queries that had been running for more than 60 seconds. Only about one-third of them were related to the earlier `version` table; **the remaining two-thirds were innocent queries dragged down by this environment**—which also confirmed that the main load source was not the `UPDATE` path. There was also another comment-related table where a join field lacked supporting indexes, which added fuel to the fire too, though not at the same scale as this count query.

## 9. Making things worse: even the last self-healing escape route was blocked

In theory, when the database hits this kind of bloat and backlog, there is still one last line of defense: `autovacuum`, which can slowly clean things up and let the situation recover on its own. But when I checked the live state, even that escape route had been blocked. The `autovacuum` process responsible for cleaning a large TOAST storage area had been stuck for **3 hours and 07 minutes** without finishing. The `autovacuum` processes on two other core tables had also been dragged down by throttling for **12 minutes 49 seconds** and **6 minutes 01 seconds** respectively, unable to make normal progress.

The fact that three `autovacuum` processes were each stuck on different tables showed this was not a localized issue on one table. The whole instance was already so resource-starved that even background cleanup tasks couldn’t get enough CPU time slices to run. **At that point, self-healing was completely impossible. Manual intervention was the only option**—which was exactly the step described earlier in section 4.

## 10. Putting the full chain together

If you connect the answers to the previous questions, the escalation path looks roughly like this:

1. Two and a half days earlier, an analytical query with parallelism started running and never exited. It not only consumed resources itself, but because its transaction stayed open for so long, it pinned the global MVCC snapshot horizon, preventing `autovacuum` from cleaning dead tuples normally, so core tables kept bloating.
2. The database had enough capacity to brute-force through more than 50 hours without obvious symptoms, until a routine traffic peak arrived. A hot count query missing the right index got amplified by concurrency into a large number of full table scans, and CPU was instantly burned through.
3. In that CPU-overloaded environment, a scheduled job that was originally protected by a distributed lock started queueing up round after round of the same `UPDATE`, because the TTL was too short and the lock was also being released early when containers were removed and restarted. It piled up to nearly 30 sessions.
4. Nowhere in the whole chain was there any statement-level timeout configured. So a large number of requests could only wait indefinitely, until the containers serving them were themselves marked timed out by health checks and removed/restarted, at which point the coroutines were passively canceled. Containers were replaced in waves—two waves in total, adding up to more than a dozen containers being marked unhealthy and restarted due to probe timeouts—which in turn fed step 3: newly started containers immediately grabbed the just-released lock and launched another round of conflicting `UPDATE`s, amplifying the loop.
5. By then, the self-healing mechanism (`autovacuum`) had already been dragged to a standstill, so only manual intervention could stop the bleeding.

With all five stacked together, the database and every service depending on it slowed down across the board. From the business side, the direct symptom was simply "all endpoints are timing out." And once those two root sources were killed, the chain snapped immediately and all metrics quickly returned to normal.

## 11. The real holes that need patching

What we did on-site was only first aid. It solved none of the root causes. After sorting it all out, there are quite a few things to fix, roughly in this priority order:

**1. Add statement-level timeouts to database connections**

I checked, and right now there is no statement-level timeout configured at all on the database connection layer (`statement_timeout` in PostgreSQL). That means how long a SQL statement can stay stuck in the database depends entirely on which outer layer times out first. Leaving this unset is basically giving every slow query an unlimited line of credit.

The setup is straightforward. PostgreSQL supports several levels, so you can choose based on need:

```sql
-- Option 1: session level, run once after connection is established; only affects the current connection
SET statement_timeout = '15s';

-- Option 2: per database role; automatically applies to all future connections for this user
ALTER ROLE app_user SET statement_timeout = '15s';

-- Option 3: instance-level default (configured in postgresql.conf or a cloud provider parameter group)
statement_timeout = 15000   -- unit is milliseconds
```

If you’re using a connection pool / ORM, it’s even better to pass it directly when creating connections, for example with Python `asyncpg`:

```python
create_async_engine(
    DATABASE_URL,
    connect_args={"server_settings": {"statement_timeout": "15000"}},  # milliseconds
)
```

The exact timeout value can’t just be guessed—you need to tier it by endpoint type. User-facing core read endpoints usually get single-digit to low double-digit seconds; background batch jobs and offline tasks can be looser, maybe tens of seconds. But **no matter which tier, it must be an explicit number, not "unset."** In this incident, the longest batch of queries was stuck for nearly 5 hours. Even if we had set a very relaxed timeout like 60 seconds, it would never have dragged on to the point where manual intervention was required.

**2. Change the scheduled job to commit in batches; the distributed lock cannot rely on a fixed TTL alone**

The table is still growing, and the one-shot large-batch `UPDATE` approach itself does not age well as data volume increases. It should be split into smaller batches with incremental commits. On the distributed lock side, having a TTL that cannot cover "how long the job might take in the worst case" is itself a hidden risk, and the lock release timing needs to be redesigned too—service restarts should not automatically mean "it is safe to release the lock and wake up the next round." Either add a renewal mechanism, or tie the lock lifecycle much more tightly to the transaction state it is protecting.

**3. Add the two indexes that are actually missing**

Add an index on the table hit by the hot count query that actually covers the real query conditions, using a non-blocking index build. Also add the corresponding index for the field used by the comment join query. This incident was also a reminder to myself: during troubleshooting, don’t decide by intuition which table "should get an index." Use `EXPLAIN` or historical load analysis tools to find the real load source first, then make changes.

**4. Add caching or periodic pre-aggregation for the hot count endpoint**, instead of doing a real-time `count(*)` every time, to reduce direct pressure on the underlying large table.

**5. Add a read replica dedicated to offline analysis**: even just having one read-only instance that does not serve online business traffic, dedicated to offline analysis and data verification queries, would avoid situations like "someone forgets to close an analysis script connection and drags down the production primary database." Letting the primary be used everywhere for ad hoc analysis creates too much risk exposure.

**6. Fill in the missing monitoring and alerts**: core database load metrics, slow SQL distribution, and so on. This incident also confirmed one thing: tools like Performance Insights, which let you inspect historical Top SQL and wait events, do cost a bit, but the difference between being able to locate the root cause in a few minutes during an incident versus not being able to is huge. For core databases, it’s worth enabling them by default.

## Summary

My biggest takeaway from this investigation is: **production incidents are rarely caused by a single factor. Most of the time, they’re several small issues that each look non-fatal on their own, but happen to line up at the same moment.** A forgotten analytical script, a hot endpoint missing an index, a distributed lock whose TTL was too short and then got released at exactly the wrong time, plus no statement-level timeout anywhere in the chain—looked at separately, each one is the kind of oversight people can easily forgive. Stack them together, and you get a very real avalanche. And because the machine itself had strong enough performance, the problem stayed latent for more than 50 hours before being triggered by a traffic peak. That kind of "delayed explosion" is even more dangerous than "immediate alerting."

Another more concrete lesson is this: **during troubleshooting, even conclusions that "look very reasonable" are worth validating with tools before you act.** At one point I was convinced it was an index issue. If I hadn’t run that extra `EXPLAIN`, I might have made a completely unnecessary index change on a nearly 800 GB table and consumed even more I/O in the process. Investigating a blocking chain can tell you who is waiting on whom, but identifying the real load source always comes back to one question: "who is actually burning CPU?" The two are not interchangeable. And when an incident happens, stopping the bleeding and giving the system room to breathe is always more important than trying to analyze everything slowly while still under pressure.