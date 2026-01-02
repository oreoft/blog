---
category: middleware
excerpt: A recent interview made it painfully clear that I’m genuinely not that good.
keywords: middleware, redis
lang: en
layout: post
title: A Deeper Look at Redis Cache Breakdown
---

## Preface

I recently went to interview at a company, and the interview experience was genuinely great—it felt like casually chatting with two big shots. But as we talked, I really felt outclassed. It was like they were peeling back the layers and I could clearly see how “green” I was: not only was my depth on specific knowledge points not deep enough, I even felt like what I was saying sounded amateurish.

What stuck with me the most: I spent forever explaining a thread-safety issue, and the senior just said, “race condition.” I spent forever explaining a split-brain issue, and the senior just said, “unreachable.” They had me completely figured out. There were a lot of interesting questions—totally worth thinking about repeatedly. Honestly, after the chat I was pretty excited, and when I got back I replayed some of the questions and thought them through again.



## Question

There was one question that really made me blush after I got home and thought about it carefully. It went roughly like this:

> We use Redis as a cache to improve throughput: check Redis first, if Redis misses then check the DB. Now a hot key expires. 100 threads come in; since they arrive at the same time, nobody hits Redis, so they all query the database and then write back to Redis. How would you improve this? There’s no standard answer—anything goes.

When I heard it, I did think for a moment, but maybe because I was nervous I didn’t react in time. It sounded super interesting at the time, but when I got home I realized: isn’t this just cache breakdown? Not gonna lie—two years ago I could already recite the “interview classics” like cache avalanche / breakdown / penetration. Yet somehow I still needed someone to explain it to me again... I just didn’t connect the dots in the moment... That’s the awkwardness of only memorizing without understanding or applying....

To be honest, I felt pretty embarrassed and also regretted not answering better, because I didn’t really understand what the scenario was getting at. I’m still too weak—just memorizing “interview answers” is useless. Sure, applying it is a bit hard; ultra-high-concurrency scenarios like this are indeed rare in real work. But I still failed to combine the knowledge point with the scenario to truly understand it.

The problem itself isn’t hard and it’s very open-ended. After thinking about it, I wrote down a few approaches. Hopefully this helps as a reference—learn by tying the concept back to the scenario.



## How to handle cache breakdown

### Key never expires (expiration time)

Set the key to never expire—one-and-done, and also a very brute-force approach.

Here, “expiration” doesn’t just mean not setting a TTL. It can also mean continuously renewing the lock (pseudo-permanent). When updating the key, write the TTL expiration timestamp together with the value. Each time you read it, compare that timestamp with the current time; if it’s about to expire, extend the timestamp inside the value.

The benefit is: for example, if I renew it when there’s 1 day left, then if this key still expires, it means there were no requests accessing it within that 1 day. In that case it’s not a hot key anymore, so there’s no need to worry about its impact on the DB. And you also avoid memory bloat caused by setting it to permanent forever.



### Method-level locking

Locking is easy to understand: add `synchronized` on the method so all requests become serialized. Only after the first request finishes will the second be allowed through. If the key expires, naturally the first request will query the table again and write back to Redis; the second request and all subsequent requests will hit Redis.

The downside is obvious: this lock is way too heavy. It serializes all requests and significantly reduces throughput. In a high-concurrency production environment, the impact is noticeable.



### Lock + serialize only when querying the DB

Lock when querying the DB. You can use a lock (remember to release it in `finally`). By narrowing the lock granularity, only requests that hit an expired key and need to query the DB will be serialized. In theory, this balances throughput and availability better.

The downside is you’re still doing wasted work: although requests won’t hit the DB concurrently, they’ll still query it one by one.



### Use a mutex so only one request queries the DB

We can improve on the previous “lock while querying DB” approach. In **Lock + serialize only when querying the DB**, when the first request comes in and queries the table, other requests are blocked. After the lock is released, they compete for the lock again and let another one in to query, until all requests are processed. But since one request is already querying the table and everyone else is blocked, can we avoid blocking and instead let the others directly read from cache after that one request finishes?

Based on this idea, it’s natural to use a mutex. Since microservices are typically distributed, here’s some Redis-based pseudocode:

```java
// 查询redis
redis = getRedis();
// 判断缓存是否过期了
if result == nil {
  // 假设同时100个请求过来，用互斥锁先放一个进去查db，这里使用setex防止死锁
  if redis.setex {
    // 查db 放缓存
    result = getDB();
    redis.set(result)
  }
  // 后面没拿到锁的都在这里cas(这里也可以设置自旋次数，防止异常情况死锁)
 while(result == nill) {
  // 查redis
  result = redis.getRedis();
 }
}
// 如果上面设置了自旋次数下面可根据业务重要性在判断若result还是为null是继续查表还是直接返回fail
```



## Afterword

This question is open-ended by nature, and scenarios like this are relatively hard to run into. Before, when I saw “cache breakdown,” people always said it would directly take MySQL down. But in reality, it might just be meaningless concurrent queries. It may hurt API performance, and with the right handling you can make these requests more “graceful.”