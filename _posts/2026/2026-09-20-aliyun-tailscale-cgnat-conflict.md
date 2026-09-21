---
layout: post
title: 在阿里云上装 Tailscale，阿里云自己的内网服务全被挡掉了
excerpt: 想把一台闲置的阿里云机器改成服务监控，装上 Tailscale 之后，DNS、apt 镜像、镜像仓库接连不通。原因是阿里云把内网服务放在 100.64.0.0/10，和 Tailscale 用的是同一个网段，Tailscale 的一条防伪造规则把它们的回包全丢了。记录一下排查过程，以及最后用的 Tailscale 官方方案。
category: cloud
keywords: tailscale, aliyun, alibaba cloud, ecs, cgnat, iptables, rp_filter, systemd-resolved, dns, 网段冲突
lang: zh
---

## 前言

我手上一直有一台阿里云的机器，是特价的时候买的，后来给它续了 20 年。配置和带宽都不高（2 核 2G，3Mbps），加上我平时管的 GCP 机器比较多，用 GCP 的时候多，这台就一直闲着。

最近想给它找点事做。我家里有几台服务器跑着一些服务，时不时会掉，有时候是机器重启了，有时候是内存溢出了。服务掉了之后，往往要等业务出了问题我才意识到，一直没有一个统一的监控。家里的机器自己就会掉，拿来监控自己不太靠谱；这台阿里云的机器配置虽然低，但胜在稳定，拿来做探活正合适。

打算用 Tailscale 把这些机器连起来。Tailscale 是一个基于 WireGuard 的组网工具，能把分散在各处的机器拉进同一个虚拟内网，每台机器分到一个 `100.x.x.x` 的地址，互相之间像在一个局域网里一样访问。我在 AWS 和 GCP 的机器上装过很多次，基本没遇到过问题。但这次在阿里云上，装完之后 DNS 解析、apt 装包、从镜像仓库拉镜像，一个接一个不通。

原因说起来就一句话：**阿里云把自己的内网服务放在 `100.64.0.0/10` 这个网段里，而 Tailscale 用的也是这个网段。** Tailscale 在 Linux 上会装一条防伪造的防火墙规则，把"不是从 Tailscale 网卡进来、却声称来自这个网段"的包全部丢掉，阿里云内网服务的回包正好被误伤。

这篇记录一下是怎么一步步查到这里的，中间试过的几种绕法，以及最后用的 Tailscale 官方方案。

p.s. 系统是 Ubuntu 22.04，Tailscale 1.102。

## 一、这台机器要做什么

先说一下打算怎么用它，后面的很多选择都和这个有关。

1. **网络接入**：把所有要监控的服务都接入 Tailscale 的内网，这台机器通过内网去调各个服务的健康检查接口，再出一个面板。
2. **访问管理**：平时在 Tailscale 内网里直接上去管理；公网只开一个 22 端口的 SSH，不在内网的时候也能从公网上去。
3. **面板查看**：在内网里直接访问面板；不在内网的时候，用 `ssh -L` 把面板端口转发到本地来看。



![整体架构](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260920223654647.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>整体架构，探活和管理都走 Tailscale 内网，公网只开放 22 端口</center><br>

探活、管理、看面板，全都走 Tailscale。所以 Tailscale 在这台机器上能不能正常工作，是整件事的前提。

## 二、装完 Tailscale，域名解析全挂了

Tailscale 装好、接入内网之后，在这台机器上解析域名，`getent hosts` 什么都没返回：

```shell
$ getent hosts github.com
$
```

先怀疑的是上游 DNS 或者出网有问题。如果是这样，指定一个公共 DNS 直接查也应该失败。去验证：

```shell
$ dig +short github.com @8.8.8.8
20.205.243.166
$ dig +short github.com
;; communications error to 127.0.0.53#53: timed out
```

指定 `8.8.8.8` 能查到，走默认就超时。出网是好的，**问题在本机的解析这一环**。

Ubuntu 22.04 默认用 `systemd-resolved` 做本地 DNS：`/etc/resolv.conf` 里写的是 `127.0.0.53`，这是它在本机开的一个转发器，真正的上游另外配置。看它用的是哪些上游：

```shell
$ resolvectl status
Link 2 (eth0)
    DNS Servers: 100.100.2.136 100.100.2.138
Link 3 (tailscale0)
    DNS Servers: 100.100.100.100
```

eth0 上那两个是阿里云 DHCP 下发的内网 DNS。`tailscale0` 上的 `100.100.100.100` 是 Tailscale 自己的 DNS，负责解析内网里的机器名，Tailscale 管这个叫 MagicDNS。

`100.100.2.136` 这个地址需要注意。Tailscale 给机器分配的地址都在 `100.64.0.0/10` 里，这是 RFC 6598 划给运营商级 NAT（CGNAT）用的保留网段，范围是 `100.64.0.0` 到 `100.127.255.255`。阿里云的内网 DNS 也落在这个范围里。

如果 Tailscale 对这个网段做了限制，阿里云 DNS 就会被波及。去看 Tailscale 在 iptables 里装的规则：

```shell
$ iptables -S ts-input
-A ts-input -i tailscale0 -j ACCEPT
-A ts-input -p udp -m udp --dport 41641 -j ACCEPT
-A ts-input -s 100.64.0.0/10 ! -i tailscale0 -j DROP
```

最后一行的意思是：**源地址在 `100.64.0.0/10` 里、但不是从 `tailscale0` 进来的包，一律丢弃。**

这条规则本意是防伪造。Tailscale 内网里每台机器的地址都在这个网段，合法的 Tailscale 流量只会从 `tailscale0` 这张虚拟网卡进来。如果有个包从物理网卡进来、却声称自己来自 `100.x`，那就是有人在冒充 Tailscale 里的机器，丢掉没有问题。

但阿里云的内网 DNS 也在这个网段。机器向 `100.100.2.136` 发查询，从 eth0 出去没问题；回包的源地址是 `100.100.2.136`，从 eth0 进来，正好命中这条规则。

![规则判定：修复前](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260920223706392.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>同一条规则下三种包的判定，伪造包和阿里云的回包在它看来是一样的</center><br>

直接验证：

```shell
$ dig +short +tries=1 github.com @100.100.2.136
;; communications error to 100.100.2.136#53: timed out
$ dig +short +tries=1 github.com @223.5.5.5
20.205.243.166
```

阿里云内网 DNS 超时，阿里云的公共 DNS `223.5.5.5`（不在这个网段）正常。对上了。

补一句，这条规则和 Tailscale 的 exit node（把一台机器作为其他设备的上网出口）功能无关，只要 `tailscaled` 在跑就会装。

其实重装系统之前体检这台机器的时候，就发现读不到阿里云的实例元数据服务 `100.100.100.200`（用来查实例 ID、安全组这类信息），原因是同一条规则。那时候只影响元数据这一项。这次换成了 DNS，影响就是全局的，所有需要解析域名的东西都用不了了。

这也解释了为什么在 AWS 和 GCP 上从来没遇到过：它们的元数据服务和 DNS 都在 `169.254.x.x` 这个链路本地网段，不在 CGNAT 段里，不会被这条规则碰到。

## 三、先把 DNS 换成公共 DNS

知道原因之后，有几个方向：

| 做法 | 问题 |
|---|---|
| 在 `ts-input` 链里加一条放行规则 | `ts-input` 是 `tailscaled` 自己管的链，每次启动都会重建，手加的规则会被冲掉 |
| `tailscale up --accept-dns=false` | 不让 Tailscale 接管 DNS，但就没法用机器名访问内网里的其他机器了 |
| 把 DNS 换成不在这个网段的公共 DNS | 能用，代价是不走阿里云内网 DNS |

当时选了第三种。阿里云的 DNS 是 DHCP 下发的，要换掉得两处一起改：先让 netplan 不再接受 DHCP 给的 DNS，再给 `systemd-resolved` 指定上游。

```yaml
# /etc/netplan/99-dns-override.yaml
network:
  version: 2
  ethernets:
    eth0:
      match:
        macaddress: 00:16:3e:xx:xx:xx
      set-name: eth0
      dhcp4-overrides:
        use-dns: false
```

```ini
# /etc/systemd/resolved.conf.d/99-public-dns.conf
[Resolve]
DNS=223.5.5.5 119.29.29.29
```

解析恢复了，MagicDNS 也不受影响，它走的是 `tailscale0` 那张网卡。

## 四、同一个问题又出现在 apt 上

DNS 修好之后去装 Docker，`apt update` 又不通了：

```
W: Failed to fetch http://mirrors.cloud.aliyuncs.com/ubuntu/dists/jammy-security/InRelease
   Unable to connect to mirrors.cloud.aliyuncs.com:http:
```

阿里云的 Ubuntu 镜像默认把软件源配成 `mirrors.cloud.aliyuncs.com`，这是阿里云的内网镜像。看一下它解析到哪：

```shell
$ getent hosts mirrors.cloud.aliyuncs.com
100.100.2.148   mirrors.cloud.aliyuncs.com
```

还是 `100.100.x.x`，同一个原因。

照着 DNS 的思路，把源换成公网镜像 `mirrors.aliyun.com`。这次能通了，但很慢：

| | 耗时 |
|---|---|
| `apt update` | 366 秒 |
| 装 Docker | 25 分钟还没装完 |

原因在带宽。**阿里云内网的流量是免费的，也不限速；走公网才要挤这台机器那 3Mbps 的带宽。** Ubuntu 一次完整的 `apt update` 要下一百多 MB 的索引，3Mbps 下就是好几分钟。原来走内网镜像根本不占公网带宽，现在内网这条路被堵了，所有流量都挤到了公网上。

到这里已经是第三次撞上同一个原因：元数据、DNS、apt 镜像。阿里云的内网服务基本都在 `100.100.x.x`，一个一个换成公网地址是在打地鼠，而且每换一个都要多占一份公网带宽。得让这个网段整体能通。

## 五、在 INPUT 链最前面放行

上面说过，规则不能加在 `ts-input` 里，它会被整条重建。但 iptables 是按顺序匹配的，`INPUT` 链只是在第一行跳到 `ts-input`。只要在 `INPUT` 链里、跳转之前先把阿里云的包放行，它们就走不到那条 DROP：

```shell
iptables -I INPUT 1 -i eth0 -s 100.100.0.0/16 -j ACCEPT
```

限定 `-i eth0` 是关键：Tailscale 自己的流量都走 `tailscale0`，不会被这条规则误放。

加上之后，内网 DNS、apt 镜像、元数据服务全都通了。

持久化之前要先确认一件事：`tailscaled` 重启的时候，会不会把自己的跳转重新插回最前面？如果会，这条规则就会被挤到第二行，等于没加。去验证：

```
# 重启前
1    ACCEPT     all  --  100.100.0.0/16
2    ts-input   all  --  0.0.0.0/0

# systemctl restart tailscaled 之后
1    ts-input   all  --  0.0.0.0/0
2    ACCEPT     all  --  100.100.0.0/16
```

**确实会。** `tailscaled` 每次启动都用 `-I` 把跳转插回第一行，手加的规则随即失效。

所以不能只是存一份 iptables 规则开机恢复，得在每次 `tailscaled` 启动之后，再把这条规则挪回第一行。写了一个跟着 `tailscaled` 走的 systemd unit：

```ini
[Unit]
After=tailscaled.service
PartOf=tailscaled.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/aliyun-internal-allow.sh

[Install]
WantedBy=tailscaled.service
```

`PartOf` 让它在 `tailscaled` 重启时跟着重启，`WantedBy` 让它在 `tailscaled` 启动时被拉起来。

脚本里还有一个时序问题：`tailscaled` 服务变成 active 的时候，它的 iptables 规则不一定已经装好了。所以先等 `ts-input` 的跳转出现，再把自己的规则挪到第一行：

```sh
for i in $(seq 1 30); do
  iptables -C INPUT -j ts-input 2>/dev/null && break
  sleep 1
done
iptables -D INPUT -i eth0 -s 100.100.0.0/16 -j ACCEPT 2>/dev/null
iptables -I INPUT 1 -i eth0 -s 100.100.0.0/16 -j ACCEPT
```

再重启一次 `tailscaled`，规则稳在第一行。然后把 apt 源和 DNS 都切回阿里云内网：

| | 公网镜像 | 内网镜像 |
|---|---|---|
| `apt update` | 366 秒 | 18 秒 |
| 装 Docker | 25 分钟未装完 | 19 秒 |

## 六、镜像仓库的内网地址不在这个段里

Docker 装好之后要拉镜像。国内访问 Docker Hub 基本不通，打算走阿里云的容器镜像服务（ACR）中转。看一下 ACR 的内网端点：

```shell
$ getent hosts registry-vpc.cn-hangzhou.aliyuncs.com
100.103.7.180   registry-vpc.cn-hangzhou.aliyuncs.com
```

`100.103.x.x`，不在刚才放行的 `100.100.0.0/16` 里，还是会被挡。

阿里云的内网服务并不都在 `100.100.x.x`，要放宽到 `100.64.0.0/10` 整段才能覆盖全。放宽之前，先去看了看别人是怎么处理这个问题的。

## 七、社区的做法，和 Tailscale 官方的方案

这个问题在 Tailscale 的 GitHub 上有一个一模一样的 issue：阿里云 ECS 装了 Tailscale 之后，内网 DNS 和 apt 全部不通，现在还开着。中文社区里也有不少文章。归纳下来有这几种做法：

| 做法 | 说明 |
|---|---|
| DNS、镜像改走公网 | 能用，但挤占公网带宽，要一个服务一个服务地改 |
| `--accept-dns=false` | 只解决 DNS，apt 和镜像仓库照样不通 |
| 手动插放行规则 | 就是上面的做法，要对付 `tailscaled` 重启时的重排 |
| `--netfilter-mode=nodivert` | Tailscale 只建规则链、不挂跳转，跳转由自己管理 |
| `disable-linux-cgnat-drop-rule` | Tailscale 官方提供的节点属性 |

Tailscale 的文档里提到，`nodivert` 是 `disable-linux-cgnat-drop-rule` 出现之前的推荐做法，现在推荐的是后者。

`disable-linux-cgnat-drop-rule` 是一个节点属性（node attribute），在 Tailscale 的策略文件里给指定的机器打上，`tailscaled` 就会把 `ts-input` 里那条 DROP 改成 RETURN：不再丢包，交给后面的规则处理。这条规则是 `tailscaled` 自己生成的，不存在被重启冲掉的问题，也就不需要我那个 systemd unit 守着了。

## 八、关掉防伪造之后，拿什么补

官方文档也说了代价：去掉这条规则，就去掉了防伪造保护，本地网络上的机器可以发一个假装来自 Tailscale 地址的包。文档给的补偿办法是打开反向路径过滤（`rp_filter`）。

`rp_filter` 是内核的一个检查：收到一个包，先查"如果我要回给这个源地址，会从哪张网卡出去"，和这个包进来的网卡对不上就丢掉。严格模式（`rp_filter=1`）要求必须是同一张。

这里要先确认一件事：如果 Tailscale 给整个 `100.64.0.0/10` 都配了一条走 `tailscale0` 的路由，那阿里云 DNS 的回包也会被判成"应该从 `tailscale0` 进来"，严格模式会把它丢掉，绕一圈又回到原点。

看 Tailscale 的路由表，它用的是编号 52 的那张：

```shell
$ ip route show table 52
100.101.102.103 dev tailscale0
100.101.102.104 dev tailscale0
100.100.100.100 dev tailscale0
```

是给每台机器单独加的主机路由，不是整段。再分别看几个地址的回程：

```shell
$ ip route get 100.100.2.136      # 阿里云 DNS
100.100.2.136 via 172.16.x.x dev eth0
$ ip route get 100.103.7.180      # ACR 内网
100.103.7.180 via 172.16.x.x dev eth0
$ ip route get 100.101.102.103    # Tailscale 里的一台机器
100.101.102.103 dev tailscale0
```

阿里云的内网服务回程走 eth0，它们也是从 eth0 进来的，一致，放行。有人从 eth0 冒充 Tailscale 里的某台机器发包，回程应该走 `tailscale0`，对不上，丢掉。

**严格模式正好补上了防伪造，而且比原来那条一刀切的 DROP 更准确：它只保护真实存在的 Tailscale 地址，不会误伤阿里云。**

![规则判定：修复后](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260920223718431.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>改成 RETURN 并打开 rp_filter 之后，同样三种包的判定</center><br>

## 九、具体改了什么

### 1. 策略文件加一个 tag 和一个节点属性

```json
"tagOwners": {
  "tag:aliyun": ["autogroup:admin"],
},
"nodeAttrs": [
  {
    "target": ["tag:aliyun"],
    "attr":   ["disable-linux-cgnat-drop-rule"],
  },
],
```

用 tag 而不是直接对自己的账号生效，是因为这个属性作用在所有 Linux 机器上，我还有一些不在阿里云上的 Linux 机器要接进来，它们没必要关掉防伪造。打 tag 可以只命中阿里云的机器。

改之前先备份了原来的策略文件，改完先调用 Tailscale 的校验接口确认没问题，再正式应用。


### 2. 给这台机器打上 `tag:aliyun`

后台的机器列表里可以改，也可以调 API。打完之后，机器上的规则马上就变了：

```
-A ts-input -s 100.64.0.0/10 ! -i tailscale0 -j DROP
-A ts-input -s 100.64.0.0/10 ! -i tailscale0 -j RETURN
```

### 3. 打开 `rp_filter`

```ini
# /etc/sysctl.d/999-ali-hz-tuning.conf
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
```

**文件名要以 `999-` 开头，这是阿里云上特有的一个坑**，下一节单独说。

### 4. 拆掉之前的 systemd unit

之前那套已经不需要了，删掉之后 `INPUT` 链里只剩 `ts-input` 一条。

### 验证

```
内网 DNS   100.100.2.136     通
apt 镜像   100.100.2.148     HTTP 200
元数据     100.100.100.200   通
ACR 内网   100.103.7.180     HTTP 401      ← 之前是超时
```

ACR 返回 401 是正常的，镜像仓库没登录就是 401。能返回说明连上了，之前是直接超时。Docker 容器联网、Tailscale 内网的 SSH、公网 SSH 也都正常。再重启一次 `tailscaled`，那条 RETURN 还在。

## 十、阿里云自带的 sysctl 会覆盖你的配置

`/etc/sysctl.d/` 下的配置文件按文件名顺序加载，**后加载的覆盖先加载的**。阿里云的镜像自带一个 `99-apsara-sysctl.conf`，里面有这几行：

```ini
vm.swappiness = 0
net.ipv4.conf.all.rp_filter = 0
net.ipv4.conf.*.rp_filter = 0
```

它把 `rp_filter` 全部关掉了。如果你的配置文件叫 `99-xxx.conf`，按顺序很可能排在 `99-apsara` 前面，开机的时候就会被它覆盖回 0。

这个坑是先在 `swappiness` 上发现的。之前调优时写的 `99-ali-hz-tuning.conf` 里设了 `vm.swappiness = 10`，用 `sysctl -p` 加载这一个文件，运行时看确实是 10。但用 `sysctl --system` 模拟开机时的完整加载，结果是 0，被 `99-apsara` 盖掉了，每次重启都会失效。

改成 `999-` 开头之后，就排在所有 `99-*` 后面了（`9` 的 ASCII 码是 0x39，大于 `-` 的 0x2d）。

还有一个细节：直接用 `ls` 看，`999-` 会显示在 `99-apsara` 前面，因为 UTF-8 的排序规则会忽略标点。但开机加载 sysctl 的 `systemd-sysctl` 用的是字节序，要看真实顺序得用 `LC_ALL=C ls`：

```shell
$ LC_ALL=C ls /etc/sysctl.d/
...
99-apsara-sysctl.conf
99-sysctl.conf
99-tailscale.conf
999-ali-hz-tuning.conf
```

**验证 sysctl 配置，要用 `sysctl --system` 看最终值，不能只用 `sysctl -p` 加载单个文件。** 后者只能说明你的文件没写错，不能说明它最后生效了。

## 十一、复盘

**1. 在阿里云上装 Tailscale，先做这几步**

- 策略文件里给阿里云的机器打一个 tag，加上 `disable-linux-cgnat-drop-rule`
- 打开 `rp_filter=1`，配置文件以 `999-` 开头
- DNS 和 apt 源保持阿里云内网的默认配置，不用改

装之前做完，就不会遇到上面这一串问题。

**2. 同一个原因出现第二次，就该找根因了**

这次元数据、DNS、apt、镜像仓库，前后撞了四次同一个原因。DNS 和 apt 是分别改成公网修的，每一次单独看都修好了，但加起来是在打地鼠，每换一个还多占一份公网带宽。

**3. 手动插的防火墙规则，要看它会不会被别的程序改掉**

`INPUT` 链上手动插的规则，在 `tailscaled` 重启之后被挤到了第二行。如果当时没去验证，这条规则会在某次重启之后悄悄失效。

**4. 先查官方文档**

社区里的做法大多是自己写脚本插规则，或者用 `nodivert`，但 Tailscale 官方已经有了专门的节点属性。早点去翻官方文档，中间那一段可以不用绕。

## 总结

这次的原因很简单：阿里云把内网服务放在 `100.64.0.0/10`，Tailscale 也用这个网段，Tailscale 的防伪造规则把阿里云内网服务的回包全丢了。AWS 和 GCP 的内网服务在 `169.254.x.x`，所以之前一直没遇到。

最后用的是 Tailscale 官方的 `disable-linux-cgnat-drop-rule`，配合 `rp_filter=1` 补上防伪造。DNS、apt、镜像仓库全部走回阿里云内网，不占公网带宽，也不用自己维护任何防火墙规则。中间改公网 DNS、改公网镜像、手动插规则，每一步当时都能用，但都只解决了眼前那一个服务，问题本身是一个网段冲突，最后也是在网段这一层解决的。

## 参考

- [CGNAT interoperability · Tailscale Docs](https://tailscale.com/docs/reference/cgnat-interoperability)
- [Tailscale netfilter modes · Tailscale Docs](https://tailscale.com/docs/reference/netfilter-modes)
- [Linux: ts-input DROP of source 100.64.0.0/10 breaks Alibaba Cloud ECS internal DNS and apt · tailscale/tailscale](https://github.com/tailscale/tailscale/issues/21249)
- [解决阿里云和 Tailscale 的 100 网段冲突的问题](https://blog.hellowood.dev/posts/resolve-alibaba-cloud-tailscale-100-network-conflict/)
