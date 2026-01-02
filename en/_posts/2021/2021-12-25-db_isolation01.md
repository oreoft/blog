---
category: middleware
excerpt: I’ve been getting asked this a lot lately, so I figured I’d put together
  a quick summary.
keywords: java, middleware, mysql
lang: en
layout: post
title: Transaction Isolation Levels in Databases
---

## Preface

Transaction isolation levels used to be one of those “must-memorize interview boilerplate” topics back when I was looking for internships and jobs. At the time I could recite them, but I didn’t really understand what they meant or how they were implemented. As I got deeper into engineering practice and accumulated more experience using databases, I started to see transaction isolation levels differently. Recently I’ve been asked about them a lot again, so I deliberately went back and reviewed Ding Qi’s *MySQL 45 Lectures in Practice*, and decided to summarize it once.

Everyone knows the ACID properties of transactions. In order to ensure these properties—especially isolation and consistency—databases generally rely on locking. Locks in databases exist to build these isolation levels. This post only introduces transaction isolation levels; the next post will analyze how MySQL’s InnoDB engine implements them.



## Database Isolation Levels

Let’s start with a table. Note: this is the isolation-level definition from textbooks. Different database implementations may vary—for example, MySQL’s InnoDB prevents phantom reads under Repeatable Read.

| Isolation Level                   | Dirty Read | Non-repeatable Read | Phantom Read                                  |
| --------------------------------- | ---------- | ------------------- | --------------------------------------------- |
| Read Uncommitted                  | Possible   | Possible            | Possible                                      |
| Read Committed                    | Impossible | Possible            | Possible                                      |
| Repeatable Read                   | Impossible | Impossible          | Possible (but impossible in MySQL InnoDB)     |
| Serializable                      | Impossible | Impossible          | Impossible                                    |

**Read Uncommitted → dirty reads**: Two transactions start at the same time. Transaction A can read changes made by transaction B that are **not committed**. That’s a **dirty read**. You don’t really need to memorize what a dirty read is—the name “Read Uncommitted” basically *is* dirty read, because it breaks isolation: two transactions should not affect each other directly.

**Read Committed → non-repeatable reads**: Two transactions start at the same time. Transaction A can read changes made by transaction B that are **already committed**. That’s a **non-repeatable read**. Same idea: you don’t need to force-memorize the definition—if you can read other transactions’ committed changes, isolation still isn’t guaranteed.

**Repeatable Read → phantom reads**: Two transactions start at the same time. Under this isolation level, changes made by transaction B (**update existing rows and commit**) won’t be visible to transaction A’s queries, meaning it can **solve the non-repeatable read problem**. **But if transaction B inserts new rows and commits, transaction A may be able to query those newly inserted rows—this is a phantom read.** The root cause is the locking mechanism. However, MySQL’s InnoDB can ensure those rows are not visible under Repeatable Read; we’ll discuss that in the next post.

**Serializable → no issues due to serialized locking**: Transactions execute serially. Each read needs to acquire a shared lock, and reads/writes block each other.

MySQL InnoDB defaults to **REPEATABLE READ** (RR below), while Alibaba Cloud RDS defaults to **Read Committed** (RC below). Next, let’s look at isolation levels through concrete SQL.



## Demo

For the database client I’m using DataGrip (DG below). In DG, open two sessions and run `begin` in each to start two transactions.

The database is MySQL 8.0. The test table DDL is:

```sql
create table t_user
(
    id     bigint unsigned auto_increment
        primary key,
    name   varchar(255) default '' not null,
    gender tinyint      default 1  not null
);
```

Test data:

```sql
insert into t_user(name, gender) values ('zhangsan', 1);
insert into t_user(name, gender) values ('wangwu', 1);
insert into t_user(name, gender) values ('xiaohong', 0);
insert into t_user(name, gender) values ('xiaohua', 0);
```

Check the current session isolation level:

```sql
# 查看当前会话隔离级别 MySQL8.0+
select @@transaction_isolation;
# # 查看当前会话隔离级别 MySQL5.0+
select @@tx_isolation;
```

Set the current session isolation level:

```sql
# 设置当前会话的隔离级别
set session transaction isolation level read uncommitted;
set session transaction isolation level read committed;
set session transaction isolation level repeatable read;
set session transaction isolation level serializable;
```



### Read Uncommitted

![image-20211225214237970](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225214238.png)

<p align="center">Set to Read Uncommitted</p>

Both windows start a transaction with `begin`. Then transaction 1 queries the row where `name='zhangsan'` and sees `gender` is 1. Next, transaction 2 updates zhangsan’s `gender` to 0. Then transaction 1 queries `name='zhangsan'` again:

![image-20211225214836782](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225214836.png)

In transaction 1’s second query result, zhangsan’s `gender` is already the value modified by transaction 2. In other words, after transaction 2 modifies the data, transaction 1 can immediately perceive it—even though transaction 2 hasn’t committed yet. This is Read Uncommitted: **reading data that other transactions haven’t committed**.



### Read Committed

![image-20211225215431583](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225215431.png)

<p align="center">Set to Read Committed</p>

Both windows `begin` at the same time. Transaction 1 queries zhangsan and sees `gender` is 1. Then transaction 2 changes zhangsan’s `gender` to 0 but does not commit. Transaction 1 queries zhangsan again and still sees `gender` is 1. After that, transaction 2 commits. Finally, transaction 1 queries zhangsan again and finds `gender` has become 0:

![image-20211225220238740](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225220238.png)

Overall, isolation is a bit better than **Read Uncommitted**, but once another transaction commits, it can still break isolation—i.e., you still get non-repeatable reads.



### Repeatable Read

![image-20211225220455896](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225220455.png)

<p align="center">Set to Repeatable Read</p>

Let’s first verify whether **Repeatable Read** solves the non-repeatable read problem:

![image-20211225220712641](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225220712.png)

You can see that under RR, the non-repeatable read problem is solved. In database specifications, RR can still cause phantom reads, but in this InnoDB experiment, transaction 1’s `select` uses MVCC snapshot reads to read historical data, ensuring isolation.

Finally, let’s distinguish **non-repeatable reads vs phantom reads**. On the surface, phantom reads focus on `insert`, while non-repeatable reads focus on `update` and `delete`. Essentially, it’s about *what data is locked* at different isolation levels. Under Repeatable Read, after the first time a SQL statement reads data, those rows are locked so other transactions can’t modify them, enabling repeatable reads. But it can’t lock rows that don’t exist yet (i.e., inserts). So when transaction 1 previously read data (or even modified all existing data), transaction 2 can still `insert` new rows and commit. Then transaction 1 will suddenly find an extra row that didn’t exist before—this is a phantom read, and it can’t be avoided with row locks alone.

### Serializable

I won’t demo Serializable, because it solves everything by serializing execution: reads use read locks, writes use write locks, and read/write locks are mutually exclusive. It effectively avoids phantom reads, non-repeatable reads, dirty reads, etc.—simple and brute-force.

## Afterword

At their core, the four transaction isolation levels are about different degrees of isolation caused by different locking mechanisms. This post summarized what isolation levels exist and what problems each level can cause. Memorize the basics first—**in the next post I’ll share how different isolation levels are achieved, and what locking mechanisms are used to solve dirty reads, non-repeatable reads, phantom reads, and so on.**