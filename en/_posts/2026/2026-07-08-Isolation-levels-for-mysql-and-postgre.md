---
category: middleware
excerpt: Hit a deadlock pitfall after switching from MySQL to PG, so I took the opportunity
  to brush up on the classic theory of isolation levels.
keywords: mysql, postgresql, database
lang: en
layout: post
title: Rethinking Transaction Isolation Levels in MySQL and PostgreSQL
---

## Introduction

I recently encountered a deadlock issue. Since I used MySQL a lot before and have now switched to PG (PostgreSQL), I took a closer look and reviewed these textbook concepts. As my engineering experience deepens, I found that I have a much deeper understanding of things I thought I knew. I'm organizing my thoughts to record this process of re-understanding.

Both MySQL and PostgreSQL follow the four isolation levels defined by the SQL standard: Read Uncommitted, Read Committed (RC), Repeatable Read (RR), and Serializable. However, their implementations under the RR level are somewhat different, which is the focus of these notes.

## 1. First, Distinguish Two Concepts: Snapshot Read and Current Read

- **Snapshot Read**: Based on MVCC, it reads a data snapshot at a specific point in time without acquiring locks. A standard `SELECT` is a snapshot read.
- **Current Read**: Reads the latest committed data and acquires locks. `SELECT ... FOR UPDATE`, `UPDATE`, and `DELETE` are all current reads—write operations must be based on the latest data; you cannot modify an old version.

The essence of an MVCC snapshot is simply a list of "which transactions have been committed and which are still ongoing" at a given moment. In PostgreSQL, every row carries an `xmin` (the ID of the transaction that created it) and an `xmax` (the ID of the transaction that deleted it). During a query, the snapshot is used to determine which row versions are visible to the current transaction.

The core difference between the two isolation levels lies in *when* this snapshot is taken:

| Isolation Level | Snapshot Timing |
|---------|------------|
| Read Committed (RC) | Takes a new snapshot at the start of **every statement** |
| Repeatable Read (RR) | Takes a snapshot only once at the first query of the **entire transaction**, and reuses it throughout |

Therefore, RC can see the latest commits from other transactions (which is where the non-repeatable read phenomenon comes from), while the world RR sees is frozen at the moment the transaction begins.

Note one easily confused point: **Read Committed does not equal Current Read**. It is still a snapshot read, just that the snapshot is "refreshed per statement." If a query runs for 10 seconds, it still won't see data committed by others at the 5th second (the snapshot was taken at second 0). Only a true current read can see that.

## 2. MySQL and PostgreSQL Take Two Completely Different Paths Under RR

This is the part I understood most deeply this time. I always thought their RR implementations were the same thing, but they are actually very different.

**PostgreSQL's RR relies purely on snapshots all the way**: Not just standard SELECTs, but even `UPDATE`, `DELETE`, and `FOR UPDATE` locate target rows based on the snapshot taken at the start of the transaction. Newly inserted rows are completely invisible to the current transaction, so phantom reads naturally do not exist. But the trade-off is that if the row you want to modify has already been modified and committed by another transaction, it will directly throw an error instead of quietly hooking you up with the latest data:

```
ERROR: could not serialize access due to concurrent update
```

**MySQL's RR is more like a "hybrid"**: Standard SELECTs live in the transaction-level snapshot, but write operations (`UPDATE`/`DELETE`/`FOR UPDATE`) always read the latest version, i.e., current read. Reads and writes might be looking at two different worlds—this is why you might clearly see `name='a'` in the snapshot, yet an `UPDATE` modifies it based on `'b'` that someone else just committed. Precisely because current reads can see newly inserted rows after the snapshot, MySQL needs **gap locks** to lock ranges and prevent insertions, plugging the phantom read loophole between snapshot reads and current reads.

A quick mental cheat sheet:

- MySQL RR = Reads use the old snapshot, writes use the latest version + gap locks as a safety net
- PG RC = Reads use a fresh snapshot (refreshed per statement), writes wait for locks and then re-check conditions on the latest version
- PG RR = Both reads and writes use the old snapshot; it throws an error immediately upon conflict

By the way, PG's RR also has a counter-intuitive loophole with `FOR UPDATE`: it can only lock rows that are already visible in the snapshot; it cannot lock (or even see) newly inserted rows from others. Therefore, "preventing new rows from being inserted within a certain range" (like preventing duplicate orders) cannot be prevented under PG's RR. You either have to upgrade to Serializable or honestly apply unique constraints.

## 3. How Useful Are the Three 'Anomalies' from the Textbooks?

Most materials discussing isolation levels will throw out this table:

| Isolation Level | Dirty Read | Non-repeatable Read | Phantom Read |
|---------|------|-----------|------|
| Read Uncommitted | Yes | Yes | Yes |
| Read Committed (RC) | Prevented | Yes | Yes |
| Repeatable Read (RR) | Prevented | Prevented | Yes in standard, but MySQL / PG implementations are stronger |
| Serializable | Prevented | Prevented | Prevented |

What these three anomalies are is pretty much explained by their names:

- **Dirty Read**: Reading data that others have **not yet committed**. The danger is straightforward—if the other transaction rolls back, what you read is data that never existed. The Read Uncommitted level is basically equivalent to having no isolation.
- **Non-repeatable Read**: Within the same transaction, the value of the same **row** changes (e.g., the first read shows a balance of 50, and after someone else commits, the second read shows 100).
- **Phantom Read**: Within the same transaction, the **set of rows** returned by a query changes (e.g., the first COUNT is 10, and after someone else inserts and commits, the next COUNT is 11). One is "the row changed," the other is "the number of rows increased/decreased."

It's worth mentioning that the standard for the RR tier only requires preventing non-repeatable reads; phantom reads can theoretically still occur. However, both MySQL and PG actually prevent phantom reads as well, just in different postures: PG conveniently blocks them using pure snapshots, while MySQL uses snapshot reads to block them for standard queries and gap locks to patch the loophole for current reads.

So overall, among these three anomalies, apart from dirty reads being a fatal flaw, the actual impact of the other two on most businesses is very limited—if you SELECT twice in the same transaction and get a few more rows the second time, whose business logic is going to break because of that? The reason these anomalies are the "standard answers" is that they are a measuring stick drawn up by the 1992 ANSI SQL standard based on "how strictly locks are applied," rather than a list of real business pain points. The anomalies that truly bite are different ones, and ironically, you won't find them in the standard table.

## 4. The Two 'Anomalies' That Actually Affect Business

These two anomalies are actually quite common. However, in my past experience writing business logic, I never thought about these issues from the perspective of transaction isolation levels. I just handled them at the application layer, thinking they were concurrency safety issues in business logic processing. In reality, they are closely related to DB transaction isolation levels, and certain isolation levels actually wouldn't have these problems.

### Lost Update

The pattern is very common: Two transactions **read the same row → calculate in memory → write back to the same row**, and the later write overwrites the earlier one.

Take inventory as an example: Inventory = 10. Transaction A reads 10 and calculates 9; Transaction B also reads 10 and calculates 9. Both execute `UPDATE stock = 9` and commit. As a result, two items are sold, but the inventory is only reduced by one. A's update is "lost" out of thin air. Note that no step in this process read dirty data—the problem lies in the fact that there is a segment of application-layer calculation between the "read" and the "write." Locks only protect the exact moment of writing; they cannot protect the causal chain of "read, calculate, and write back."

There are three standard ways to prevent this:

```sql
-- 1. Atomic update: Compress read and write into a single statement with locks
UPDATE inventory SET stock = stock - 1 WHERE id = 123 AND stock > 0;

-- 2. Pessimistic locking: Lock first, then read
SELECT * FROM inventory WHERE id = 123 FOR UPDATE;

-- 3. Optimistic locking: Rely on version numbers, retry if affected rows is 0
UPDATE inventory SET stock = stock - 1, version = version + 1
WHERE id = 123 AND version = 5;
```

The performance of isolation levels here also shows a clear winner: **MySQL's RR cannot prevent it**—`UPDATE` is a current read, so it still modifies based on the latest value. **PG's RR naturally prevents it**—when B tries to commit, it finds that the row has been modified and committed after its own snapshot was taken, so it directly rolls back with a serialization error, forcing you to retry.

### Write Skew

Pattern: Two transactions **read the same range → make decisions based on the results → each writes to different rows**.

The classic example is an on-call roster: The rule is "at least 1 person must be on call." Right now, both Alice and Bob are on call. Transaction A queries and finds 2 people on call, decides "I can get off work," and changes **Alice's row** to not on call. Transaction B simultaneously queries and finds 2 people on call, and changes **Bob's row** to not on call. Neither side read the wrong data, and their respective judgments hold true in the worlds they see, but after both commit, the number of people on call becomes 0.

The most fatal part here is: **The write sets of the two transactions have absolutely no intersection**; no single row was touched by both simultaneously. Row locks won't conflict, PG RR's snapshot check won't detect that any row "has been modified," and optimistic locking version numbers have nowhere to apply—because what broke isn't the value of a specific row, but a business invariant spanning multiple rows. It doesn't belong to any single row, so row-level mechanisms inherently cannot govern it.

Prevention methods need to move up a dimension:

- In MySQL, you can use `SELECT ... FOR UPDATE` to lock the read range first, forcing the other transaction to queue up;
- In PG, you can directly use **Serializable**. It relies on predicate locks to record "who read what conditions" (e.g., `on_call = true`). Once the read-write dependencies of two transactions form a cycle, one will be judged as non-serializable upon commit, directly throwing an error and rolling back;
- A more clever workaround is **data modeling convergence**—store the "number of people on call" separately as a counter field. The write skew then degrades into a standard lost update, and row-level locks immediately become effective.

Comparing the two anomalies side-by-side makes it clearer:

| | Lost Update | Write Skew |
|---|---|---|
| Read | Same row | Same range |
| Write | **Same row** (overwrite each other) | **Different rows** (no contact with each other) |
| What breaks | The value of a specific row | Cross-row business invariants |
| Row Lock / Optimistic Lock | Effective | Ineffective |
| Can PG RR prevent it? | Yes | No |
| Can MySQL RR prevent it? | No | No |

To summarize in one sentence: Lost update is "two transactions modify the same cell, and the later commit overwrites the earlier one"; write skew is "each modifies their own cell, but everyone's decision is based on the assumption that the other hasn't made a move yet."

## 5. Why Can't We Just Leave It All to Isolation Levels?

Seeing this, a natural thought arises: Since Serializable can block all the above problems, why not just enable Serializable globally?

Because the cost is too high. Under Serializable, predicate locks themselves have overhead, and after a conflict, the entire transaction rolls back and starts over, not just re-running a single statement—the longer the transaction, the greater the loss from a rollback, and "rollback storms" might even occur on hot rows. The vast majority of business scenarios modify different rows and don't need this strong guarantee at all, yet they would have to pay the application-layer cost of "having to write retry logic" for it.

So a more realistic approach is **using Read Committed as the baseline, and using specific weapons for specific problems**: unique constraints to prevent duplicate inserts, atomic updates or optimistic locking to prevent lost updates, and `FOR UPDATE`, Serializable, or modeling convergence to prevent write skew. Leaving the work outside of isolation levels to the application layer might seem like "not letting the database do everything," but it trades off for better concurrency and lower intrusiveness.

This also explains the divergence in the default values of the two databases:

- **PostgreSQL chooses RC**: Good concurrency, no gap locks, and upon write conflicts, it just waits for the lock, re-checks the conditions, and continues running without easily throwing errors. It's much friendlier for throughput in short-transaction, high-concurrency Web scenarios, and since non-repeatable reads and phantom reads don't hurt the business that much anyway, RC is a default that takes care of most scenarios.
- **MySQL chooses RR**: This is mostly historical baggage. Early MySQL master-slave replication relied on `statement` format binlogs, replaying SQL statements exactly as they were—if RC was used, the commit order and execution order of concurrent transactions would be inconsistent, and the replay results might not match the master database.

  Therefore, in the early days, RR + gap locks had to be used to ensure replication consistency. Later, the `row` format was introduced in 5.1 and became the default after 5.7, basing replication on actual row changes rather than the statements themselves. This limitation actually no longer exists, but the default isolation level wasn't changed back and has been kept to this day. Precisely because of this, for many internet companies today (including in Alibaba's guidelines), the first thing they do when getting a new database is manually tune it to RC.

## 6. How Were These Anomalies Originally Defined?

Looking back, why can't we find truly harmful anomalies like lost updates and write skew in the standard table? The 1992 ANSI SQL standard used three anomalies—dirty reads, non-repeatable reads, and phantom reads—to define isolation levels. This set of definitions was a product of adapting to pure lock implementations back in the day. In 1995, Berenson et al. wrote a famous paper, "A Critique of ANSI SQL Isolation Levels," specifically criticizing this standard for being too crude. They pointed out that it missed real-world anomalies like lost updates and write skew, and conveniently defined "Snapshot Isolation"—which is the theoretical prototype of PostgreSQL's RR. It is stronger than ANSI's RR (can prevent lost updates) but weaker than Serializable (cannot prevent write skew), fitting perfectly into the gaps of the standard. It wasn't until 2008 that someone proposed the SSI (Serializable Snapshot Isolation) algorithm, adding dependency cycle detection on top of snapshot isolation, which PostgreSQL 9.1 implemented as its own Serializable level.

In other words, textbooks are still teaching that map from the 90s, while the real evolution of the industry has been moving forward along the line of snapshot isolation. The truly harmful anomalies aren't on the old map, but they have always been in the territory.

## Conclusion

After all this tinkering, I feel that isolation levels are actually useful and not just pure textbook boilerplate. Most data safety indeed still relies on application-layer constraints and idempotent design as a safety net, but the deeper you understand isolation levels, the better you know which direction to think when encountering extreme concurrency scenarios—whether to add a unique constraint, use optimistic locking, or just accept fate and write retry logic. Choosing an isolation level is essentially less important than first recognizing what kind of threat model you are facing.