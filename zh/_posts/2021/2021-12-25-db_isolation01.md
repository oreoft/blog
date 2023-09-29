---
layout: post
title: 数据库的事务隔离级别
excerpt: 最近总被问特意总结一下
category: middleware
keywords: java, middleware, mysql
lang: zh
---

## 前言

事务隔离级别原来实习找工作的时候是必背八股文了，当时只会背却没深刻理解里面的意思和具体实现，随着工程实践的深入，对数据库使用的积累，对事务隔离级别有不一样的认识。最近又常常被问到，然后特意去复习了一遍丁奇大大的《MySQL实战45讲》，就想着总结一遍。

大家都知道事务的ACID性质，数据库为了让事务能保证这些性质尤其是隔离性和一致性，一般都会采用加锁的方式来做到。数据库中的锁是为了构建这些隔离级别来存在的。本篇只介绍事务隔离级别，下一篇会分析MySQL中InnoDB引擎中事务隔离级别的实现。



## 数据库隔离级别

先上表格，要说明的是这是教材中数据库隔离级别，不同的数据库实现会有不一样，例如MySQL的innoDB就在可重复读的情况下防止了幻读。

| 隔离级别                   | 脏读   | 不可重复读 | 幻读                          |
| -------------------------- | ------ | ---------- | ----------------------------- |
| 读未提交(Read Uncommitted) | 可能   | 可能       | 可能                          |
| 读已提交(Read Committed)   | 不可能 | 可能       | 可能                          |
| 可重复读(Repeated Read)    | 不可能 | 不可能     | 可能(若MySQL的InnoDB则不可能) |
| 可串行化(Serializable)     | 不可能 | 不可能     | 不可能                        |

**读未提交-导致脏读**：两个事务同时开启，事务a可以读到另外一个事务b的**未提交**的修改内容，这个其实就是**脏读**，不用特意去记脏读是什么，读未提交的名字其实就是脏读，因为它破坏了隔离性，两个事务直接应该是互不影响的。

**读已提交-导致不可重复读**：两个事务同时开启，事务a可以读到另外一个事务b的**已提交**的修改内容，这个其实就是**不可重复读**，也不用特意去记不可重复读是什么，读到其他事务已提交的内容也没有保证隔离性。

**可重复读-导致幻读**：两个事务同时开启，在这个隔离级别下事务b**更改记录并且提交**不会被事务a查询到，也就是说可以**解决重复读问题**。**但是当事务b对数据进行插入新增数据并且提交，这条新数据会被事务a所查询到，这成为是幻读**。具体原因是因为加锁机制导致的，但是MySQL的innoDB在可重复读的情况下可以可以保证不被查询到，下一篇会讨论。

**串行化读-串行化加锁不存在任何问题**：两个事务是串行执行的，每次读都需要获取标记的共享锁，读写相互都会堵塞。

MySQL的innoDB默认是**REPEATABLE READ**(下称RR)，阿里云的RDB默认是**Read Committed**(下称RC)，下面通过具体的sql来看事务隔离级别。



## 演示

数据库连接工具我是用的是DataGrip(下称DG)，在DG开两个会话分别开始begin表示开启两个事务。

数据库使用的MySQL8.0版本，测试的表DDL如下

```sql
create table t_user
(
    id     bigint unsigned auto_increment
        primary key,
    name   varchar(255) default '' not null,
    gender tinyint      default 1  not null
);
```

产生的测试数据如下

```sql
insert into t_user(name, gender) values ('zhangsan', 1);
insert into t_user(name, gender) values ('wangwu', 1);
insert into t_user(name, gender) values ('xiaohong', 0);
insert into t_user(name, gender) values ('xiaohua', 0);
```

查看当前会话隔离级别

```sql
# 查看当前会话隔离级别 MySQL8.0+
select @@transaction_isolation;
# # 查看当前会话隔离级别 MySQL5.0+
select @@tx_isolation;
```

设置当前会话隔离级别

```sql
# 设置当前会话的隔离级别
set session transaction isolation level read uncommitted;
set session transaction isolation level read committed;
set session transaction isolation level repeatable read;
set session transaction isolation level serializable;
```



### 读未提交

![image-20211225214237970](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225214238.png)

<p align="center">设置成读未提交</p>

两个窗口的事务都开始`begin`，然后事务1先查询`name='zhangsan'`的数据，发现zhangsan的gender是1，然后事务2在更新zhagnsan的gender为0，然后事务1再查询`name='zhangsan'`的数据

![image-20211225214836782](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225214836.png)

最后的事务1中的第二次查询结果，zhangshan的gender是事务2修改以后的数据，也就是说事务2修改数据后，在事务1中查询可以立马感知到，哪怕是事务2都没有提交这个事务。这就是读未提交，**也就是读到其他事务未提交的数据**。



### 读已提交

![image-20211225215431583](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225215431.png)

<p align="center">设置成读已提交</p>

两个窗口的事务同时`begin`，然后事务1先查询zhangsan发现gender是1，然后事务2对zhangsan的gender修改成0后不提交事务，然后事务1再次查询zhangsan的gender还是1，随后事务2对事务进行提交，最后事务1再次查询zhangsan的gender发现已经被修改成0了

![image-20211225220238740](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225220238.png)

总的来说隔离性比**读未提交**稍好一些，但是其他事务提交事务请求后依然会破坏隔离性，也就是没有达到不可重复读。



### 可重复度

![image-20211225220455896](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225220455.png)

<p align="center">设置成可重复度</p>

我们先来验证这个**可重复度**是否解决了不可重复读的问题

![image-20211225220712641](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211225220712.png)

可以看到RR的隔离级别下已经解决了不可重复读的问题，在数据库规范中RR隔离级别下其实还会导致幻读，但是实验中的InnoDB中事务1进行select会读取MVCC的快照读进行历史数据的读取，来保证隔离性。

最后做一个区分，**不可重复读和幻读的区别**。表面上的区别在于幻读的重点在insert，但不可重复读重点在于update和delete，本质上是隔离级别锁住的数据不同，在可重复读中，执行SQL第一次读取到数据后，就将这些数据加锁，其它事务无法修改这些数据，然后就可以进行重复读了。但是却无法锁住insert的数据，所以当事务1先前读取了数据，或者修改了全部数据，事务2还是可以insert数据提交，这时事务1就会发现莫名其妙多了一条之前没有的数据，这就是幻读，不能通过行锁来避免。

### 串行化

可串行化(Serializable)就不演示了，因为它通过串行来解决所有问题，读用读锁，写用写锁，读锁和写锁互斥，来有效的避免幻读、不可重复读、脏读等问题，简单粗暴。

## 后言

四种事务隔离级别本质就在于通过锁机制导致的隔离性不一样，这篇总结了有哪些隔离级别，不同隔离级别会导致哪些问题。先背好，**下一篇将分享不同事务隔离级别是怎么做到的，脏读、不可重复读、幻读等问题是使用什么锁机制来解决。**
