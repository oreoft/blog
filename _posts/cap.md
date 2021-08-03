---
layout: post
title: MacOS自定义快捷键一键休眠
excerpt: 找了很久终于找到优雅的方式了
category: other
keywords: other, macos
---

# 状态机复制的共识算法



## ZAB

#### 消息广播

1. ZAB的消息广播过程类似于二阶段提交，客户端发送的请求全部都是leader接受(如果有follower接到了请求也需要转发给leader)
2. 客户端向Leader发起写请求
3. Leader将写请求以Proposal的形式发给所有Follower并等待ACK
4. Follower收到Leader的Proposal后返回ACK
5. Leader得到过半数的ACK（Leader对自己默认有一个ACK）后向所有的Follower和Observer发送Commmit
6. Leader将处理结果返回给客户端

#### Leader选举

1. 当leader结点崩溃以后，整个集群进入选举模式，其他结点会根据事务id和机器id两个标准进行选举投票，这样可以保证选举出来的leader含有最新的数据
2. leader选举之后，整个集群恢复广播模式

#### 崩溃恢复

1. leader在给所有结点发送通知消息崩溃了，其他结点会重新进行选举，这个消息会被丢弃。
2. leader在给部分结点发送执行消息后崩溃了(这里是发送执行)，其他结点会进行重新选举，选出出来的结点一定是收到这个消息的结点，然后新leader会重新保证这个事务数据一致。



## Raft

#### Leader选举

1. 每个结点会有一个timeout的到期时间，一旦到期这个结点就会认为自己的leader，就会给其他结点发送心跳，其他结点收到心跳以后知道这个结点是leader结点。
2. 如果同时有两个到期结点发到心跳给对方，双方认为自己是leader结点然后收到了别人的心跳，这两个会重新一轮timeout，因为这两个leader都是继续等待timeout，另外结点没收到心跳会有一个提前到期，然后主动发送心跳给其他的结点，最终竞选出leader



#### 日志复制

1. 客户端给leader提交消息
2. leader并不会第一时间把消息持久化(因为raft也是基于cp)
3. leader第一时间会在下一次心跳里通知所有的follower，leader会等待所有的follower的响应
4. 如果有半数follower响应(注意follower只是响应，还没有写入)，leader会把自己的值进行更新，给客户端发送成功ack消息，然后再正式向follower发起写入通知
5. 期间如果是有半数没有响应则leader会放弃这个消息

每个客户端的请求都会被重定向发送给leader，这些请求最后都会被输入到raft算法状态机中去执行

> leader在收到这些请求之后，会首先在自己的日志中添加一条新的日志条目
>
> 在本地添加完日志之后，leader将向集群中其他节点发送AppendEntries RPC请求同步这个日志条目，当这个日志条目被成功复制之后，leader节点将会将这条日志输入到raft状态机中，更新commitedIndex,通知应用层进行数据的持久化，持久化成功之后就可以更新appliedIndex,然后应答客户端
>
> leader节点会在每次heartbeat或者AppendEntries的请求中带上committedIndex,这样followerer节点就能够提交日志并应用持久化数据




#### 安全性

1. 如果其中有结点挂了，会有安全机制来保证数据的一致。
2. 如果leader给follower发送消息后宕机了，那么follower的结点会在等到超时时间后进行重新选举，选举后整个通知事务并不会马上执行，会在这个新leader接受新消息，然后下一次发送心跳通知的时候执行。
3. 如果leader给部分follower发送消息后宕机了，并且恰好没收到消息的结点timeout到了，会给其他结点发送竞选心跳，其他结点收到会判断index值，发现index值没有自己的维护的高则会拒绝投票，然后其他收到消息的结点timeout到了以后会重新竞选。竞选完毕以后这个消息的执行(第一次是事务的通知不是执行)会随下一次接收新消息的心跳通知执行
4. 如果leader给一个follower发送消息宕机了，其他follower都没收到，然后有一个没有收到消息的结点timeout到期了，这个时候它想要竞选他会收到一个否决票然后收到大多数的同意票。这个结点会竞选成功，并且在下个消息把收到消息的那个结点的数据给覆盖掉



https://juejin.cn/post/6844904196819402760



https://toutiao.io/posts/1bforz/preview