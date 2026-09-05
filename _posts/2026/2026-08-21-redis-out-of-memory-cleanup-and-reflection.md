---
layout: post
title: 一次生产 Redis 内存打满的排查、清理和复盘
excerpt: 线上 Redis 内存到了 99.98%，开始逐出数据。先用 SCAN 把内存分布摸清楚，再按 LRU 空闲时间清掉一半冷数据释放 4GB，最后复盘背后的几个架构问题
category: middleware
keywords: redis, elasticache, oom, eviction, lru, idletime, architecture
lang: zh
---

## 前言

今天收到一条监控报警：生产环境的主 Redis 内存使用率直接飙到了 **99.98%**，而且监控大盘上的 `Evictions`（逐出 Key 数量）开始不断往上涨。

这个指标一旦报警其实挺危险的，因为我们这台实例配的淘汰策略是 `allkeys-lru`。也就是说，在内存完全打满的情况下，Redis 为了能继续写入新数据，会开始按 LRU 策略随机淘汰旧 Key。而这台 Redis 上同时还跑着用户的 Session、接口限流计数器、以及一些业务基础缓存，要是任由它这么无差别逐出，核心业务数据被误杀只是时间问题。

既然确认了 Redis 确实满了，第一步肯定不是慌着乱删，而是要先把情况摸清楚：**分析内存占用分布 -> 找出大头 -> 制定安全清理方案 -> 根治隐患**。

记录一下这次排查过程、按空闲时间清理冷数据的脚本，以及事后复盘出来的几个架构问题。

<img src="https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260821235633107.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80" alt="QQ_1787374585754" style="zoom:25%;" />

<center>（配图占位：CloudWatch / Datadog 监控大盘上 Redis 内存飙到 100% 且 Evictions 开始递增的图）</center><br>

## 一、线上不能盲猜：全库 Key 内存分布分析

面对一个被打满的生产 Redis，第一大忌就是凭感觉去删 key，第二大忌是图省事直接敲 `KEYS *` 或者 `FLUSHDB`（前者会导致单线程直接卡死，后者会把线上业务全干崩）。

必须先搞清楚到底是谁在吃内存。我写了个轻量级的 Python 脚本，通过 `SCAN` 游标分批遍历全库，采样统计每个前缀的 Key 数量和预估内存占用。

当时跑出来的全库内存分布大概是这样的（关键业务前缀已做脱敏）：

| Key 前缀（脱敏） | Key 数量 | 数量占比 | 单 Key 均值 | 预估占用内存 | 业务性质 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`prod:search_emb:*`** | **58.5 万** | **22.8%** | **14.5 KB** | **~8.07 GB (87.5%)** | **搜索 Query 向量缓存** |
| `prod:img_url:*` | 106.3 万 | 41.4% | 537 B | ~544 MB (5.9%) | 图片预签名 URL 缓存 |
| `service_go:prod:*` | 18.8 万 | 7.3% | 1.95 KB | ~350 MB (3.8%) | 微服务加速缓存 |
| `prod:card_cache:*` | 3.8 万 | 1.5% | 2.03 KB | ~72.7 MB (0.8%) | 运营卡片缓存 |
| `prod:session:*` | 42.8 万 | 16.7% | 136 B | ~55.5 MB (0.6%) | 用户 Session 状态 |
| `prod:qclass:*` | 17.1 万 | 6.7% | 211 B | ~34.4 MB (0.4%) | 分类打标缓存 |
| `prod:user:*` / `LIMITS:*` | ~3 万 | 1.2% | 100~400 B | ~15 MB | 用户信息、限流等核心业务 |

看到这个表，问题就很清楚了：整个实例可用内存 **9.2 GB** 左右，`prod:search_emb:*` 这一个前缀就占了 **8.07 GB（87.5%）**。Session、限流这些核心业务加起来只占很小一部分，是被这一个前缀挤掉的。

用于分析全库分布的非阻塞脚本如下：

```python
import redis

r = redis.Redis(host="your-redis-host", port=6379, socket_timeout=10)

cursor = 0
stats = {}

while True:
    cursor, keys = r.scan(cursor=cursor, count=5000)
    for k in keys:
        k_str = k.decode("utf-8", errors="replace")
        parts = k_str.split(":")
        prefix = parts[0] + ":" + parts[1] if len(parts) >= 2 else parts[0]
        
        if prefix not in stats:
            stats[prefix] = {"count": 0, "sample_bytes": 0, "sample_cnt": 0}
        
        stats[prefix]["count"] += 1
        if stats[prefix]["sample_cnt"] < 50:
            m = r.memory_usage(k)
            if m:
                stats[prefix]["sample_bytes"] += m
                stats[prefix]["sample_cnt"] += 1
    if cursor == 0:
        break

total_keys = sum(s["count"] for s in stats.values())
print(f"Total keys: {total_keys}")
for p, s in sorted(stats.items(), key=lambda x: x[1]["count"] * (x[1]["sample_bytes"]/max(1, x[1]["sample_cnt"])), reverse=True):
    avg_m = s["sample_bytes"] / max(1, s["sample_cnt"])
    est_mb = (s["count"] * avg_m) / (1024 * 1024)
    print(f"{p:<30} | {s['count']:>8} | {avg_m:>8.1f}B | {est_mb:>10.2f} MB")
```

## 二、翻看代码：这个大头能不能清理？

定位到前缀后，立刻去代码库里翻对应的实现。

发现这是在做语义搜索时，为了加速对用户搜索词（Query）调用大模型（LLM）计算出的 1024 维 Embedding 向量。

代码里的逻辑是标准的 **Read-Through（旁路读穿）** 模式：
1. 用户输入搜索词，先去 Redis 查这个 Query 的 embedding 在不在；
2. 如果命中（Cache Hit），直接拿存好的向量去向量库做检索；
3. 如果未命中（Cache Miss），调用大模型 API 生成 1024 维向量，然后写回 Redis，并设置了一个 **3 天（`ex=3*86400`）** 的 TTL。

这就解释了为什么会有 58 万个 key：在最近几天的搜索量下，用户搜索的词各不相同，3 天的积累硬生生堆出了 8GB 的向量数据。

### 能不能清？怎么清？
从业务逻辑上看，它本身就是个加速缓存，清掉不会引起任何数据不一致或业务报错——因为只要缓存没有，代码就会自动去 LLM 回源重新生成。

但**能不能全部删掉？不行**。
如果一口气把 58 万个向量全抹掉，线上正在跑着搜索请求，瞬间全量 Cache Miss 会导致所有并发搜索全部涌向底层的 LLM 模型 API，瞬间把下游的大模型接口打出限流或者超时，反而引发更大的次生故障。

所以最好的解法是：**既要把内存降下来，又不能全部清空，优先清理那些最冷门、很久没被访问的数据，保留热点缓存。**

## 三、精细化清理：按命中率（Idle Time）精准清理最冷 50%

那么问题来了，Redis 里怎么判断哪些向量缓存是“很久没被命中过的冷数据”？

答案是利用 Redis 原生的 **`OBJECT IDLETIME key`**。
在 `allkeys-lru` 模式下，Redis 会给每个 key 记录一个 LRU 时钟。通过 `OBJECT IDLETIME`，可以精确查出这个 key 距离上一次被读取/写入已经过去了多少秒（这个查询只读时钟，完全不会改变 key 的访问时间）。

我们先用 Pipeline 跑了一下全量 58.5 万个向量 key 的空闲时间分布：

| 空闲时间（距上次命中） | Key 数量 | 占比 | 决策 |
| :--- | :--- | :--- | :--- |
| **> 2 天（48小时以上无人访问）** | 14.9 万 | 25.59% | **准备清理（极冷数据）** |
| **1 ~ 2 天（24~48小时无人访问）** | 14.4 万 | 24.72% | **准备清理（冷数据）** |
| **12 ~ 24 小时** | 11.8 万 | 20.28% | **保留（温数据）** |
| **6 ~ 12 小时** | 6.9 万 | 11.82% | **保留（活跃数据）** |
| **1 ~ 6 小时** | 8.0 万 | 13.73% | **保留（高频热数据）** |
| **< 1 小时** | 2.2 万 | 3.86% | **保留（核心热数据）** |

数据很清楚：**空闲时间 24 小时以上（一天以上没人搜过的词）占了 50.3%，29.4 万个。**

这 29.4 万个 key 大概率是一些冷门长尾搜索词，留着除了吃内存毫无收益。而剩下的 49.7% 都是在过去 24 小时内有命中记录的热门词。

### 执行安全异步清理

为了保证对生产业务 0 影响，我们使用 `SCAN` 游标 + `Pipeline` 批量判断 + **`UNLINK`**（后台线程异步释放内存，不阻塞主线程），每批 1000 个，批次间休眠 10ms：

```python
import redis
import time

r = redis.Redis(host="your-redis-host", port=6379, socket_timeout=10)

# 阈值：24 小时以上未被命中的冷数据
IDLE_THRESHOLD = 86400 

cursor = 0
total_scanned = 0
total_unlinked = 0
batch_to_delete = []

print(f"清理前内存: {r.info('memory').get('used_memory_human')}")

while True:
    cursor, keys = r.scan(cursor=cursor, match="prod:search_emb:*", count=2000)
    if keys:
        pipe = r.pipeline(transaction=False)
        for k in keys:
            pipe.object("idletime", k)
        idles = pipe.execute()

        for k, it in zip(keys, idles):
            total_scanned += 1
            if it is not None and it >= IDLE_THRESHOLD:
                batch_to_delete.append(k)

            # 每凑齐 1000 个调用一次异步 UNLINK
            if len(batch_to_delete) >= 1000:
                r.unlink(*batch_to_delete)
                total_unlinked += len(batch_to_delete)
                batch_to_delete = []
                time.sleep(0.01)  # 短暂停顿，避免主线程抖动

    if cursor == 0:
        break

if batch_to_delete:
    r.unlink(*batch_to_delete)
    total_unlinked += len(batch_to_delete)

time.sleep(2)
print(f"清理完成! 共扫描 {total_scanned} 个，异步清理冷 Key {total_unlinked} 个")
print(f"清理后内存: {r.info('memory').get('used_memory_human')}")
```

### 清理效果
脚本跑了大约 20 秒：
- 扫描 585,152 个 Key，精准删除了 **294,350 个冷 Key（占比 50.30%）**；
- Redis 内存从 **9.19 GB 降到 5.22 GB**，释放了 **4.0 GB**；
- 内存水位从 **99.98% 降回 56.5%**，`Evictions` 归零，Session 等核心业务的报警解除；
- 下游 LLM 接口没有出现流量冲击。

<img src="https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260822000031624.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80" alt="QQ_1787374821275" style="zoom:25%;" />

<center>（配图占位：清理完成后，内存使用率降回 56% 且业务恢复平稳的监控大盘图）</center><br>

## 四、事后复盘：暴露出哪些架构问题？

虽然问题在十几分钟内解决了，但这次内存打满暴露了架构上的几个问题：

### 1. 序列化方式太浪费（JSON 字符串 vs 二进制 pack）
去看了代码才发现，这个 1024 维的 float 向量写入 Redis 时，直接调了 `json.dumps(vector)`。
一个 1024 维的浮点数组，转成 JSON 字符串后每个浮点数带一大堆小数位，加上逗号括号，单个 key 占了 **14.5 KB ~ 21 KB**！

但实际上，1024 个 `float32` 用 Python 的 `struct.pack('<1024f', *vector)` 压成二进制，只有固定的 **4096 字节（4 KB）**，哪怕为了兼容做个 Base64 也就 5.5 KB。
如果一开始就用二进制 pack，同样的 key 数量，内存直接能砍掉 **62%**，原本 8GB 的数据直接能降到 3GB 以下。

### 2. 大体积加速缓存与核心业务共用实例（未做物理隔离）
这台 Redis 实例目前混放了两类东西：
既承担着搜索向量、URL 预签名等**大体积、允许丢失、可重新计算**的旁路加速缓存，又承担着 Session、用户信息、接口 Rate Limit 限流等**小体积、低延迟、绝不能丢**的核心业务。

一旦某个旁路缓存逻辑上线或者流量暴涨，就会立刻侵占整个实例的内存，导致核心业务的 key 被 LRU 驱逐。
这两类应该物理拆开：**搜索/算法等高消耗缓存**和**核心业务 Redis** 分到不同实例。

### 3. 实例规格本身偏小
当前这台主实例选型是 `cache.r4.large`（总物理内存 12GB，扣除 25% 预留内存后 Redis 可用只有 9.2GB）。
相比之下，我们的推荐系统等重度计算服务的 Redis 实例普遍都用到了 64GB 规格。随着搜索和 AI 功能用得越来越多，9.2GB 已经跟不上了，后续要升配或者迁移。

## 总结

线上排查高危组件的故障，节奏往往是：**先用监控指标快速定性 -> 用只读/低开销手段定位根因 -> 权衡业务风险制定最小代价的止血方案 -> 最后从代码和架构层面堵死漏洞**。

这次按 LRU 空闲时间切一刀，把内存压回了安全线，也尽量保住了命中率。更重要的是复盘出了序列化、实例隔离和容量规划这几个要补的地方。
