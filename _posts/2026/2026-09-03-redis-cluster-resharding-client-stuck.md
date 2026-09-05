---
layout: post
title: redis加了个分片，把线上写挂了一个多小时
excerpt: Redis 内存满了，清了一轮冷数据只下来 5 个 G，索性直接加一个分片扩容。结果 slot 刚开始迁移 12 秒，推荐服务的 ZADD 就开始疯狂报错。以为是服务没感知到新节点，重启一下就好，结果重启完还在报。顺着那句"reachable node:None"往下挖，最后挖到 redis-py 客户端里一行"节点超时就从名单里删掉"的代码上。
category: middleware
keywords: redis, valkey, elasticache, redis-py, cluster, resharding, moved, 生产事故, 客户端 bug
lang: zh
---

## 前言

起因是推荐系统用的那个 Redis 内存又满了，`used_memory` 顶到 **79.34G / 79.36G（99.98%）**，`Evictions` 也开始往上涨，说明它已经在往外扔数据了。

先试着清了一轮。这个库里最大的一块是曝光历史（`device_imp:*` 这种，记录哪个设备看过哪些内容，用来做推荐去重），占了一半以上的内存，就拿它开刀，按 LRU 的 idle time 清 30 天以上没被访问过的。

清完效果一般。原因也简单，30 天以上没访问过的基本都是流失用户，这批人压根就不怎么用我们的产品，曝光历史本来也没几条。忙活半天清掉 88 万个 key，内存才下来 5 个 G，基本等于白折腾。

于是同事给出了行动项，一方面是缩减 ttl，另外一方面直接了加一个分片。

ElastiCache 加分片是在线操作，官方宣传就是不影响业务，我们连的也是 cluster 模式的配置端点（`clustercfg.xxx`），客户端理论上会自动感知拓扑变化。

结果就是这个"理论上"，让线上的曝光写入挂了一个多小时，所以加了分片看一下应用层情况，以及 claster  move 是否正常，虽然是无感但是线上业务还是得有敬畏之心，果不其然，加完就出问题了。

## 一、加完分片 12 秒，就开始报错了

先把 ElastiCache 的事件时间线拉出来（时间都是 UTC）：

```
05:11:29  Scaling out replication group from 1 node groups to 2 node groups
05:15:39  Modified replication group to add 1 new node groups - 0002
05:17:18  Migrating slots from node groups 0001 to 0002 to rebalance slots   ← 开始搬 slot
05:21:24  Moved a total of 8192 slots out of 8192 slots from shard 0001 to shard 0002
```

应用侧第一条报错的时间是 **05:17:30**，比 slot 开始迁移晚了 12 秒。

而前面那 12 分钟，从 05:11 开始扩容、到 05:15 新分片建好，一条错都没有。加节点、建 shard 都平安无事，偏偏 slot 真正开始搬动的那一刻炸了。

报错长这样：

```
ERROR | app.service:215 - info_collect failed,
exception_type=RedisClusterException,
exception=Redis Cluster cannot be connected. Please provide at least one reachable node: None
```

Datadog 上那条曲线特别直观，之前一直贴着 0，然后直接立起来：

![QQ_1788505007127](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260904015652175.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>step.exception 这个指标之前一直是 0，slot 开始迁移之后直接跳到 2k-3k / 2min，然后一直维持在那</center><br>

按这个量级换算，每秒有 17~25 个请求的曝光记录写不进去。

这里插一句，`info_collect` 是我们推荐流程里的一个 step，它干三件事，顺序很关键：

```python
ctx.response.items = rsp_items        # 1. 先把要返回给用户的推荐结果组装好
self.stats(ctx)                       # 2. 打点
await PosterMgr.run_all(ctx, ...)     # 3. 最后才写曝光记录到 Redis  ← 在这一步炸
```

响应在第 1 步就已经装好了，第 3 步炸了并不影响用户拿到推荐。所以这次故障从头到尾**接口全程 200，没有超时，没有 5xx，也没有任何用户报障**，是完全静默的。要不是我当时正好在翻这个 Redis 的 key 分布，可能还得再挂一阵子。

## 二、以为重启就完事了，结果没好

看到"cannot be connected"，第一反应特别自然：服务启动的时候只有一个分片，现在多了一个，它不知道啊。老进程手里拿的是旧的拓扑，重启一下重新拉一次不就完了。

于是重启。

**重启完，还在报。**

这就有点意思了。而且更让人迷惑的是，去翻启动日志，初始化明明是成功的：

```
06:01:41 | app.core.database_manager:299 - Redis Cluster connection initialized -
          host=clustercfg.xxx-redis.xxx.cache.amazonaws.com, port=6379,
          max_connections=300, use_tls=True
```

一条 `initialization failed` 都没有。也就是说，**进程启动的时候是连得好好的，跑着跑着自己坏掉了**。

后来对了下时间，06:02 初始化成功，06:09 就开始报错，大概 7 分钟就复发一次。重启只能续命几分钟。

到这一步，"服务没感知到新节点"这个假设就站不住了。新进程明明感知到了，是跑了一会儿又忘了。

## 三、报错最后那个 None，才是真正的线索

后来把完整的 traceback 捞出来看，才注意到一个细节：

```
File "/usr/local/lib/python3.11/site-packages/redis/asyncio/cluster.py", line 685, in execute_command
    await self.initialize()
File "/usr/local/lib/python3.11/site-packages/redis/asyncio/cluster.py", line 392, in initialize
    await self.nodes_manager.initialize()
File "/usr/local/lib/python3.11/site-packages/redis/asyncio/cluster.py", line 1300, in initialize
    raise RedisClusterException(
redis.exceptions.RedisClusterException: Redis Cluster cannot be connected.
Please provide at least one reachable node: None
```

<img src="https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260904020221262.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80" alt="QQ_1788505311066" style="zoom:25%;" />

一开始我觉得这句报错没什么信息量，"至少给一个能连的节点"，那不就是网络不通吗？可网络明明是通的，我从跳板机上手连这个集群一点问题都没有。

问题出在最后那个 `None` 上。去翻 redis-py 的源码，那句异常是这么拼出来的：

```python
exception = None
for startup_node in self.startup_nodes.values():
    try:
        cluster_slots = await startup_node.execute_command("CLUSTER SLOTS")
        startup_nodes_reachable = True
    except Exception as e:
        exception = e          # ← 连不上的话，错误存在这里
        continue

if not startup_nodes_reachable:
    raise RedisClusterException(
        f"...Please provide at least one reachable node: {str(exception)}"
    )
```

如果真是连不上，`exception` 里应该躺着一个 `ConnectionError` 或者 `TimeoutError`。它是 `None`，说明这个 for 循环压根一次都没进去，也就是 `self.startup_nodes` 是空的。

**不是连不上节点，是客户端手里已经没有节点可连了。**

## 四、客户端手里的节点是怎么没的

顺着这条线继续翻 redis-py 的代码，在 `execute_command` 的异常处理里找到了这个（我们线上用的是 `redis==5.0.0`）：

```python
except (ConnectionError, TimeoutError):
    # Connection retries are being handled in the node's Retry object.
    # Remove the failed node from the startup nodes before we try
    # to reinitialize the cluster
    self.nodes_manager.startup_nodes.pop(target_node.name, None)   # ← 就是这行
    await self.close()
    raise
```

节点一超时，就把它从 startup_nodes 里删掉。这个设计的假设是"还有别的节点可以用来重新发现拓扑"。

但这里还有第二个坑，我在跳板机上实测了一下：

```
构造客户端时:      startup_nodes = [clustercfg.xxx...]
第一次初始化之后:  startup_nodes = [0001-001, 0002-001]   ← 被发现到的真实节点覆盖了
```

**你配的那个 `clustercfg` 配置端点，第一次初始化成功之后就被丢掉了**，换成了当时发现到的具体节点。

两个坑加在一起才是致命的：

```
扩容之前是单分片 → 首次初始化后，名单里只有 {0001-001} 这一个节点
                    （clustercfg 已经被覆盖没了）
    ↓
05:17:18 开始搬 slot，连接抖动，抛 ConnectionError/TimeoutError
    ↓
startup_nodes.pop("0001-001")   → 名单空了
    ↓
await self.close()              → 标记需要重新初始化
    ↓
之后每一条命令 → initialize() → 遍历空名单 → exception 一直是 None
                → raise "...reachable node: None"
    ↓
永久卡死，进程不重启就出不来
```

所以从单分片扩容特别容易中招，名单里就一个节点，pop 一次就空了。要是本来就是多分片，删掉一个还剩别的，大概率能自己爬回来，我们恰好是最惨的那个场景。

还有一点当时挺困惑的，日志里从头到尾没有任何 timeout 的报错。后来想明白了，那个 ConnectionError 是在 redis-py 内部的重试循环里被消化掉的，pop 完就 `raise`，外层重试逻辑接住之后再调一次 `initialize()`，这次撞上空名单，抛出来的就变成 `RedisClusterException` 了，应用层只看得到最后这个。**日志里没有 timeout，不等于没发生过 timeout。**

## 五、这不是新问题，GitHub 上早有人踩过

搜了一下，redis-py 仓库里有一模一样的 issue：

> **[RedisCluster becomes unrecoverable if all nodes timeout · Issue #3221](https://github.com/redis/redis-py/issues/3221)**

标题就是我们的症状。里面明确指出元凶就是 `startup_nodes.pop` 那行，还提到在单节点集群配置下特别严重，跟我们的情况完全对上。

还有一个相关的：

> **[async redis cluster should use initial startup nodes during reinitialization in case of failover · Issue #2472](https://github.com/redis/redis-py/issues/2472)**

这个说的就是第二个坑，async 版本在首次初始化时会覆写你配的 startup nodes。

两个 issue 加起来，就是我们这次事故的完整拼图。比较无奈的是 **#3221 的状态是 `closed as not planned` + `stale`**，官方没把它当回事，挂到自动关闭了。

## 六、为什么另一个服务没受影响：版本差了三个大版本

排查的时候有个现象一直想不通，我们另一个后端服务也连着这个集群，也经历了同一次扩容，它一点事没有。

一开始我以为是写法的区别：

```python
# 另一个服务：直接传 host/port
RedisCluster(host=host, port=port, ssl=..., decode_responses=True, ...)

# 推荐服务：传 startup_nodes
startup_nodes = [ClusterNode(host=host, port=port)]
RedisCluster(startup_nodes=startup_nodes, ssl=..., ...)
```

拿同一个版本做了个对照实验，结果两种写法行为完全一样，都会被覆盖，都会卡死。`host=`/`port=` 在 redis-py 内部只是被转成一个 `ClusterNode` 塞进 `startup_nodes` 而已，最后走的是同一条路。

那就只剩一个变量了，版本：

```
另一个服务  : redis[hiredis]~=8.0.0      → uv.lock 锁的是 8.0.0
推荐服务    : redis==5.0.0               → traceback 里的路径证实就是它
```

差了整整三个大版本。去 8.0.0 的源码里翻同一个位置，那行 pop 已经没了：

```python
# 5.0.0 —— 直接把节点从名单里删掉
self.nodes_manager.startup_nodes.pop(target_node.name, None)

# 8.0.0 —— 不删了，只把失败节点排到队尾，稍后再试
target_node.update_active_connections_for_reconnect()
await target_node.disconnect_free_connections()
self.nodes_manager.move_node_to_end_of_cached_nodes(target_node.name)
e.last_failed_node_name = target_node.name
```

名单永远不会空，也就永远不会出现 `reachable node: None`。

同一个集群、同一次 slot 迁移、两个服务，一个卡死一个没事，唯一的变量就是客户端版本，变量控制得比做实验还干净。

这里顺便说个容易搞混的点。**客户端的版本号和服务端 Engine 的版本号并不是一一对应的关系**，redis-py 8.x 里那个 8 和 Valkey 8.2 里那个 8 没有直接关系，对不上也照样能跑。我们服务端是 Valkey 8.2.0（`INFO` 里 `redis_version` 还会报 7.2.4，那是 Valkey 为了兼容老客户端故意伪装的），客户端一个 5.0.0 一个 8.0.0，连接和读写都正常。

但"能跑"不代表就该这么一直放着。**服务端内核版本往上走了，客户端最好也跟着走，别差太远**，我觉得这才是这次真正的收获。原因有两条：

一是新内核的特性，老客户端根本吃不到。协议层面的 RESP3、新加的命令、客户端缓存这些，都得客户端配套支持才用得上，服务端单方面升上去等于白升。

二是老客户端身上会积着一堆早就修掉、但你还没享受到的 bug。**我们这次就是撞在第二条上**，5.0.0 是 2023 年 8 月的版本，中间三个大版本的修复一个都没拿到，那行 pop 就在其中。

所以升级的理由得分清楚：不是"版本号必须跟服务端对齐"，而是"客户端不能长期不动"。这个区分还是有用的，不然下次容易推出很离谱的结论，比如"那把服务端降回去是不是也行"（不行，bug 在客户端，跟服务端版本没关系）。

## 七、临时方案：加个 watchdog

当时的处境是根因知道了，但半夜升级一个跨三个大版本的客户端库风险太大，所以先上了个 watchdog 兜底。

思路很简单，既然客户端会把自己搞成一个永远出不来的状态，那就在外面盯着，发现坏了就整个丢掉重建：

```python
async def _watchdog(self):
    while True:
        await asyncio.sleep(self.WATCHDOG_INTERVAL_SECONDS)   # 10 秒
        ping_task = asyncio.ensure_future(self.client.ping())
        done, _ = await asyncio.wait({ping_task}, timeout=self.WATCHDOG_PING_TIMEOUT_SECONDS)
        if ping_task not in done:
            ping_task.cancel()      # 慢 ping 按瞬时问题处理，不重建
            continue
        error = ping_task.exception()
        if error is None or not isinstance(error, RedisClusterException):
            # 只有 RedisClusterException 才代表进了不可自愈的状态；
            # 超时这类瞬时错误客户端自己能恢复，重建反而添乱
            continue
        # 用最初的配置端点重新造一个
        new_client = await self._build_client()
        old_client, self.client = self.client, new_client
        await old_client.close()
```

有两个点当时特意注意了一下：

1. 重建必须用最初的配置端点（clustercfg），不能用客户端当前手里的节点，它手里那份已经是坏的了。
2. 只对 `RedisClusterException` 重建。一开始想的是报错就重建，后来觉得不行，网络抖一下就重建容易搞出重建风暴，而且那种情况客户端自己能恢复。

检测间隔配的是 10 秒，意味着最坏情况会丢 10 秒的曝光。跟"永久卡死等人工重启"比，这个代价可以接受。

白天的时候把 Redis 这边也处理了一遍，跑了验证，问题才算真正收住。恢复之后的数据对比很清楚（20 秒窗口）：

| | 故障中 | 恢复后 |
|---|---:|---:|
| 0001 分片 MOVED | +5,567 | +1 |
| 0001 分片 ZADD 被拒 | +5,560 | +0 |
| 0002 分片 ZADD 成功 | +0 | +5,656 |
| 0002 分片总命令数 | +28 | +16,902 |

新分片终于开始接流量了，写入按 slot 正常分成了两半。

<img src="https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260904015735296.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80" alt="QQ_1788505052649" style="zoom:33%;" />

<center>watchdog 上去之后，step.exception 掉回了正常水位</center><br>

这里还有个小插曲。曲线掉下来了，但没归零，还剩 14% 左右。查了下发现有一个旧版本的实例没被替换掉，7 个实例里 1 个是旧的，1/7 = 14.3%，跟残留的比例正好对上，停掉它就干净了。

## 八、复盘：几个比 bug 本身更值得记的点

**1. 最麻烦的不是报错，是不报错**

这次故障接口全程 200，没超时没 5xx 没有用户投诉，曝光写入丢了一个多小时，幸好我观察一下。

根源在这段代码：

```python
try:
    await step_ins.do_process(ctx)
except Exception as e:
    logger.error("{} failed, ...", step_name, ...)
    datadog_agent.increment("step.exception", tags=["step:" + step_name])
    continue      # ← 吞掉，继续下一个 step
```

这个 `except + continue` 的写法本身没错，曝光写失败确实不该让整个推荐接口挂掉。**问题是这个降级没有配套的告警。** 指标其实一直在打，只是没人给它设阈值。一个能吞掉三分之一写入的故障，指标就那么躺了一个多小时没人看，这个才是真正该补的洞。

**2. "重启一下试试"是会骗人的**

重启之后错误确实少了一阵，很容易让人以为"好了，再观察观察"。实际上是新进程从干净状态起来，撑了 7 分钟又踩进同一个坑。判断有没有真的好，不能只看错误量降没降，要看它降到多少、有没有归零、会不会反弹。

**3. 云厂商说的"在线扩容不影响业务"，指的是服务端**

服务端确实做到了，整个过程 `cluster_state: ok`，16384 个 slot 全程有归属，数据一条没丢。**但客户端能不能跟上拓扑变化是另一回事，那是你自己的责任。**

以后再做这种拓扑变更，操作清单里应该加一条：变更完之后去每个分片上看一眼 `INFO commandstats`，确认新分片真的在接业务流量。这次新分片持有一半 slot、433 万个 key，业务命令数却是 0，这个信号已经很明显了，可惜我们是事后才想到去看。

## 总结

这次最大的感受是，故障链条上每一环单看都挺"合理"的。

云厂商的在线扩容没问题，服务端全程健康；我们用了 cluster 客户端，连的是配置端点，写法也没错；异常被 catch 住做降级，避免了整个接口挂掉，听起来还是个好实践。就是这么一堆各自看都没毛病的东西凑到一起，加上客户端库里一行"节点超时就删掉"的代码，最后变成了一次持续一个多小时、完全静默的线上故障。

另一个收获是关于排查方法的。中间我推翻了自己四个假设，"拓扑过期导致重试耗尽"、"5.0.0 连集群这件事本身就是坏的"、"重新初始化会清空名单"、"close 的时候会清空名单"，每一个当时都觉得挺有道理，最后都被实验推翻。真正把问题钉死的，反而是报错末尾那个孤零零的 `None`。

不过绕了这么一大圈，最后的结论其实挺朴素的：**这就是个版本问题**。5.0.0 里那行 pop 是实打实的 bug，8.0.0 已经改掉了，同一个集群、同一次扩容，跑 8.0.0 的服务没受影响。

所以最实际的一条经验还是前面那句：**服务端内核版本往上走了，客户端也别落太远**。新特性用不上还算小事，真正要命的是那些你本该白拿、却因为没升级而错过的修复。平时风平浪静看不出差别，一旦做了扩缩容、failover 这类拓扑变更，欠的债会一次性还给你。我们这次隔了三个大版本没动过，算是把利息一起还了。
