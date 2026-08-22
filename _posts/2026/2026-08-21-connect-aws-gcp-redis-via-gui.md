---
layout: post
title: 如何优雅地在本地 GUI 客户端连接 AWS / GCP 的内网 Redis
excerpt: 告别繁琐易断的 SSM 端口转发，教你用 SSH 隧道给桌面客户端配置丝滑的多环境 Redis 直连
category: cloud
keywords: aws, redis, elasticache, ssm, ssh-tunnel, gcp, memorystore, jumpbox
lang: zh
---

## 前言

最近在线上排查一个 Redis 内存快被打满的问题，想去翻翻到底是哪些 key 在疯长、有没有大 key 或者没设 TTL 的数据。这种时候最直观的做法，肯定是在本地开个 GUI 工具（比如 Another Redis Desktop Manager、RedisInsight 之类的客户端），连上去搜一下或者可视化翻一翻。

但只要你在 AWS 或者 GCP 上用过托管的 Redis，大概率都遇到过同一个槛：**云厂商的 Redis 根本不给你开公网的机会**。

先说个免责声明：在合规流程极严的大厂，从本地直连生产环境 Redis 可能会被安全团队重点问候。但在很多 Startup、小团队，或者作为技术负责人、运维处理紧急故障时，能快速、直观地观测和诊断线上数据，比折腾一堆审批流要敏捷得多。

今天就顺手记录一下为什么云厂商死活不给 Redis 开公网，以及我是怎么从折磨人的 SSM 命令行转发，切换到在 GUI 客户端里用 SSH 隧道优雅直连的。

## 一、为什么 RDS 能开公网，Redis 坚决不行？

刚开始用云服务的时候，我其实觉得这事有点反直觉：在 AWS 或者 GCP 上买个 RDS (PostgreSQL / MySQL) 或者 Cloud SQL，只要你想，控制台点一下就能分配 Public IP，安全组配个自己的 IP 白名单，本地就能直接连。

但到了 ElastiCache 或者 GCP Memorystore for Redis，控制台根本连“公网访问”这个开关都没做，直接强制锁在私有子网（Private Subnet）里。

这其实真不是云厂商故意偷懒，而是 Redis 本身的一些特性决定的：

1. **历史包袱与脆弱的防爆破能力**：Redis 最初的设计假设是运行在**绝对可信的内网环境**，早期版本甚至连密码认证都没有。即便现在有了 Auth 和 ACL，因为 Redis 单机每秒能硬扛几十万次请求，黑客用字典在公网上暴力破解密码的成本极低。
2. **高危命令与脚本逃逸风险**：Redis 的权限边界很宽，像 `CONFIG SET`、`EVAL`（Lua 脚本）或者模块加载功能，历史上都出现过通过未授权访问/弱密码，利用 Lua 脚本沙箱逃逸直接往宿主机写文件、反弹 Shell 的严重漏洞。
3. **单线程模型极易被阻塞**：Redis 核心处理是单线程的。如果直接暴露在公网，哪怕遇到很小流量的恶意请求，或者有人不小心发了个高开销的 `KEYS *`，整个 Redis 实例会瞬间卡死，导致下游所有业务雪崩。

所以云厂商的底线很统一：**不管你怎么配，Redis 实例只能留在 VPC 内网**。

## 二、为什么用 AWS SSM 端口转发总觉得难受？

既然不能直连，传统做法就是找一台同一 VPC 下的 EC2 跳板机，用 AWS 官方的 SSM 做本地端口转发：

```bash
aws ssm start-session \
  --target i-0123456789abcdef0 \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["my-redis-prod.xxxxxx.ng.0001.use1.cache.amazonaws.com"],"portNumber":["6379"],"localPortNumber":["6379"]}'
```

命令跑起来之后，本地就相当于把 `127.0.0.1:6379` 映射到了云上的 Redis，GUI 客户端直接填 `localhost:6379` 就能连。

在代码里偶尔跑一次本地测试，这种方式确实挺方便。但如果你经常要在管理工具里看数据，就会发现它有几个很搞心态的痛点：

- **多环境切换极其繁琐**：平时一般都有 `dev`、`stage`、`prod` 好几套环境，偶尔还有推荐系统或者搜索专用的 Redis。每次想切环境，都得先去终端 `Ctrl+C` 停掉，改一下 host 参数重新跑；或者在本地开 `6379`、`6380`、`6381` 一堆端口，时间一长自己都忘了哪个端口对应哪个环境。
- **闲置频繁断连**：SSM 的 session 是有心跳和超时机制的。稍微离开电脑一会儿没发请求，或者笔记本合盖休眠了一下，终端里的连接就悄悄断了（经常卡在 `Waiting for connections...`）。切回 GUI 工具一点刷新直接报超时，又得去终端里重来一遍。
- **必须常驻终端窗口**：每天屏幕上都要多占一个跑着 SSM 的终端 Tab，生怕手抖给关了。

## 三、换个思路：用本地密钥直接打通跳板机

其实现在的 Redis 桌面客户端（像 Another Redis Desktop Manager、RedisInsight 等）基本都原生支持 **SSH Tunnel（SSH 隧道）**。

![QQ_1787373870235](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260821234439597.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>（配图占位：桌面客户端中的 SSH Tunnel 配置界面，可在 review 时替换）</center><br>

如果直接让桌面客户端自己去管 SSH 隧道，把每个环境的 Redis 保存成独立的连接卡片，点哪个就自动拉起隧道，用完自动休眠，体验就会顺滑很多。

很多朋友卡在这一步，往往是因为**跳板机以前的 pem 密钥找不到了、或者权限过期了**。

其实既然你本地有敲 AWS SSM 命令的权限，那完全不需要找人重新要 key，直接用 SSM 把自己本地新生成的一个公钥，一键写进跳板机里就行。

### 1. 本地生成专用的 SSH 密钥对
在本地终端执行一条命令，生成一个标准的 RSA 密钥对（不设密码，方便 GUI 工具直接加载）：

```bash
# 生成专用于 Redis 隧道的密钥
ssh-keygen -t rsa -b 2048 -m PEM -f ~/.ssh/my_redis_tunnel.pem -N "" -C "redis_tunnel_key"
```

### 2. 用 AWS SSM 把公钥无感注入跳板机
找到同一 VPC 下那台有公网 IP 的跳板机 EC2 实例 ID，直接一条 CLI 命令下发脚本，把公钥追加到跳板机的 `authorized_keys` 中：

```bash
PUB_KEY=$(cat ~/.ssh/my_redis_tunnel.pem.pub)

aws ssm send-command \
  --instance-ids "i-0123456789abcdef0" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[
    \"mkdir -p /home/ubuntu/.ssh\",
    \"chmod 700 /home/ubuntu/.ssh\",
    \"echo '$PUB_KEY' >> /home/ubuntu/.ssh/authorized_keys\",
    \"chmod 600 /home/ubuntu/.ssh/authorized_keys\",
    \"chown -R ubuntu:ubuntu /home/ubuntu/.ssh\"
  ]"
```

> **原理很简单**：AWS SSM Agent 在 EC2 内部是以 `root` 权限跑的后台守护进程，它接收到 AWS API 的指令后直接把你的公钥写进白名单，彻底绕过了“为了放公钥必须先登录服务器”的死结。

### 3. 在 Redis 客户端里配置连接

现在跳板机已经认你的本地私钥了，打开 Redis 桌面客户端新建连接：

1. **基础连接（General）**：
   - **主机 (Host)**：填 Redis 的内网 Endpoint（如 `my-redis-prod.xxxxxx.ng.0001.use1.cache.amazonaws.com`）
   - **端口 (Port)**：`6379`
   - **密码 (Auth)**：没设密码就留空
   - **TLS / Cluster**：按实际情况选（标准主从通常不勾选）
2. **SSH 隧道（SSH Tunnel）**：
   - **勾选** ☑️ `SSH`
   - **地址**：填跳板机的公网 IP（如 `54.xxx.xxx.xxx`）
   - **端口**：`22`
   - **用户名**：`ubuntu`（或系统的默认用户名）
   - **私钥**：浏览选中刚才生成的 `~/.ssh/my_redis_tunnel.pem`
   - **密码 / Passphrase**：留空

点击测试连接，直接一把过。

## 总结

这样配完之后，整个开发体验会有很大改观：

你可以在 GUI 客户端里把 `Prod-Redis`、`Stage-Redis`、`Dev-Redis` 分别存成独立的连接配置。所有的连接共享同一个跳板机和私钥，但内网 host 各自独立。以后排查问题想看哪个环境，双击直接连上，断线了客户端也会自动重连，彻底告别了在后台挂一堆 SSM 终端命令的日子。

在日常开发和运维过程中，很多基础设施的安全策略（比如内网隔离）是必须遵守的底线，但通过合理利用跳板机和客户端原生能力，完全可以在守住安全边界的同时，把本地的排查效率拉满。
