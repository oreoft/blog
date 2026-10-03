---
layout: post
title: 把跑满杂活的 Windows 小主机改装成 PVE
excerpt: 家里那台零刻小主机在 Windows 上堆了一堆服务，Hyper-V、WSL2、Windows Docker 轮番试过，稳定性始终上不去。这次干脆把宿主机换成 PVE，Windows、Linux、飞牛、黑苹果各开一台虚拟机，按需分配。
category: other
keywords: pve, proxmox, windows, docker, hyper-v, wsl2, 黑苹果, 小主机, homelab, 折腾
lang: zh
---

## 前言

家里有一台零刻 SER 小主机，CPU 是 R7 5800H（8 核 16 线程），两根 16G 的 DDR4 3200 内存，一块 1T 的 NVMe SSD。家里的宽带有公网 IP，所以它一直 7×24 小时开着，当家里的小服务器用。

它一直装的是 Windows，身上的活越堆越多，稳定性却一直上不去。这篇记录一下我为什么最后把它整个重装成 PVE，怎么装的，装完之后机器是怎么分的。中间顺手拆机清了一次灰，有几张图。

p.s. 这篇偏经历和思路，不是一步一步的教程。

## 一、Windows 上的活越来越多

一开始它就是一台普通的 Windows 电脑，后来给它安排的活越来越多：

1. **一些服务**：几个自己写的服务（比如一个 AI 服务）、ddns-go（自动把家里变化的公网 IP 更新到域名上）、一个 nginx 网关，还有 hy2 这种代理的小工具。
2. **NAS 和智能家居**：飞牛 OS 和 HAOS（Home Assistant 的系统）。
3. **Windows 专属的应用**：有几个应用只有 Windows 版，只能在 Windows 上跑。

这里面真正离不开 Windows 的只有第三类，前两类都是被 Windows "顺带"托着的。

## 二、稳定性一直上不去

Windows 当宿主机，问题主要有两个：

1. **Windows 本身很占资源**。系统盘动不动几十 G，后台一堆我用不上的服务，内存也被吃掉一大块。
2. **它会自己重启**。更新策略再怎么调，隔一阵子还是会找机会重启一下。宿主机一重启，上面所有服务一起断，飞牛也跟着断。

## 三、跑服务的方案，换了三轮

为了让那些服务跑得稳一点，我前后换过三种方案。

### 1. Hyper-V 时代

最早是在 Hyper-V（Windows 自带的虚拟机）里开 Linux 虚拟机跑服务，飞牛也一直是这么跑的。用下来有三个问题：

1. **资源占用重**。每台虚拟机都要完整跑一个 Linux 系统，服务一多，每一台都要占一份系统的开销。
2. **断电后自启不稳**。有时候断电再来电，虚拟机自己起来也会出问题。
3. **整体太重**。后来觉得 WSL 更轻量，就改用 WSL 了。

### 2. WSL2 时代

WSL2 是 Windows 里跑 Linux 的子系统，比开虚拟机轻不少，但又遇到了新问题：

1. **网络麻烦**。WSL 虽然支持镜像网络（让 WSL 和 Windows 共用同一套网卡和 IP），但配起来非常麻烦。
2. **和宿主机传文件容易出错**。服务的日志、一些零碎的小文件放在 Windows 那边，WSL 默认的文件共享方式在两边同时改的时候会报错。后来改成走 SMB 共享，才好一点。
3. **没事就自己退出**。上面明明有服务在跑，WSL 也会自己退掉，我只好在 Windows 这边再写一个保活脚本。

### 3. All In Docker based on Windows

所以后面就直接在 Windows 上装 Docker，所有服务都放进去。不过 Windows 上的 Docker 本质上也是开了一个 WSL，只是这个 WSL 是 Docker 专属的，里面跑的其实还是 Linux 版的 Docker。所以多出来的那一层还在，坑也还在。

举个印象最深的：Docker 在 Windows 上转发 UDP 端口要多经过一层，偶尔会出现**容器明明活着，端口却已经不通了**的情况。为了这个，我专门给 hy2 配了一个"伴生"容器：每 30 秒真的去握手一次，失败就发告警并自动重启服务。能用，但这种补丁本身就说明底子不对。除此之外还有一些其他乱七八糟的问题，反正就是很麻烦。

三种方案换下来，问题始终在宿主机这一层：只要宿主机是 Windows，它的重启、它的资源占用、它对 Linux 生态的那层转译，就绕不过去。

## 四、为什么换 PVE

这台机器的性能其实挺好的，没必要把所有东西都压在一个 Windows 上。

PVE（Proxmox VE）是一个基于 Debian 的虚拟化系统，装在物理机上当宿主机，网页上就能管理虚拟机和容器。换成它之后，思路就变成了：

1. **宿主机只做虚拟化**，自己不跑业务，也不会莫名其妙地重启。
2. **需要 Windows 的时候，开一台配置低一点的 Windows 虚拟机**，专门跑那些只有 Windows 版的应用。
3. **其他服务交给一台稳定的 Linux 虚拟机**，所有 Docker 应用都在里面原生跑，不再有转译层。
4. **飞牛、HAOS 这类系统，各自一台虚拟机**。

这样每个系统多少核、多少内存都能按需分，哪台出问题就重启哪台，互不影响，备份和快照也是 PVE 自带的。一劳永逸，以后加东西也更方便。

## 五、开工之前，先清个灰

动手之前，先把机器拆开清一下灰。

![](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003100309797.jpg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>两根 16G 内存，右边是 1T 的 SSD</center><br>

里面就是那两根 16G 的内存，还是在内存涨价之前买的，旁边是 1T 的 SK Hynix NVMe SSD。整体来说配置还是非常不错的。

清到底盖的时候，眼前一黑：**原来我一直都没撕 SSD 那块导热垫上的保护膜。**

![03-ssd-film](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095647224.JPG?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>底盖上的导热垫，蓝色那截就是没撕的保护膜</center><br>

清灰的时候还看到底盖上有一个 SATA 接口，我就想起手上正好有一块 2.5 寸的机械硬盘。

![](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003100159596.jpg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>从硬盘盒里拆出来的老机械盘</center><br>

这是从一台很老的苹果电脑上拆下来的盘，十几年前的了。拆下来之后一直没怎么用，就当备用盘，当时还给它买了个硬盘盒当移动硬盘用。现在有了 NVMe 的移动硬盘盒，它就更用不上了。干脆放进小主机里，以后当备用盘或者存储盘。

![](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095643186.jpg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>把机械盘装进底盖的硬盘位</center><br>

老硬盘比较厚，虽然也是 2.5 寸，但有 9.5mm，其实不太塞得进去，塞完之后底盖还有点鼓起来。不过把 4 个角的螺丝拧紧之后，其实也没有翘起来特别多。

![](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095629924.jpg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>装完之后底盖鼓起来一点</center><br>

就是"肚子"圆鼓鼓的，看起来有点滑稽，不过不影响使用。这块盘后来格式化了，专门给 PVE 存虚拟机备份。

## 六、先把数据搬走

我的 Mac 有 8T，放这些迁移的数据绰绰有余，所以全部先往 Mac 上搬。真正要搬的数据其实不多：

1. **飞牛的虚拟盘**：原来有 250G。先把里面的大文件单独拷出来，再在飞牛里回收空闲空间、压缩虚拟盘，最后只剩 33G。
2. **各个服务的配置和数据**：加起来就 2G 左右。Docker 镜像、代码仓库都能重新拉，不用带。

拷完都校验过一遍，再开始动机器。

![06-copy-fnos-files](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095548355.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>先把飞牛里的大文件拷到 Mac 上，两百多 G</center><br>

![07-fnos-fstrim](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095544443.webp?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>在飞牛里跑 `fstrim`，回收了 257G 空闲空间，虚拟盘才压得下来</center><br>

## 七、调 BIOS，装 PVE

先在 Mac 上把 PVE 的镜像写进 U 盘。

![09-dd-iso](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095452415.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>用 `dd` 把 PVE 9.2 的镜像写进 U 盘</center><br>

然后进 BIOS 改了几项：

1. 打开虚拟化：SVM（AMD 的 CPU 虚拟化）和 IOMMU（设备直通要用）。
2. 来电自动开机：断电恢复后不用人去按电源键。
3. 核显显存给到 1G(之前是 3G, 因为给宿主机win，可能平时用的上， 现在可以调低把内存让出来了)
4. 系统模式调成性能模式，打开 CPPC（让系统能更细地调 CPU 频率，PVE 那边的调频驱动要靠它）。

![10-bios-main](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003094607877.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>BIOS 首页，R7 5800H 加 32G 内存</center><br>

![11-bios-svm](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095355337.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>打开 SVM</center><br>

![12-bios-iommu](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095457700.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>打开 IOMMU</center><br>

![13-bios-ac-loss](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095348920.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>来电自动开机</center><br>

![15-bios-performance-mode](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003101926989.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>系统模式调成 Performance Mode</center><br>

![16-bios-cppc](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095421546.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>打开 CPPC</center><br>

改完从 U 盘启动，装 PVE 9。

![17-pve-installer](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095312969.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>PVE 的安装界面</center><br>

![18-pve-disk](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095011684.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>系统装在 1T 的 SSD 上，文件系统选 ext4</center><br>

![19-pve-network](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095033142.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>给宿主机配一个固定的局域网 IP</center><br>

装完之后做了一点调优：CPU 调度直接拉到性能模式。这台机器插着电 7×24 跑，**我不在乎功耗，只在乎性能**。

## 八、分机器

现在 PVE 上一共四台虚拟机：

| 虚拟机 | 系统 | 配置 | 干什么 |
|---|---|---|---|
| ser-docker | Debian 13 | 4 核 / 4G | 所有 Docker 服务 |
| ser-fnos | 飞牛 OS | 4 核 / 4G | NAS，原来的虚拟盘直接导进来 |
| ser-win | Windows Server 2025 | 4 核 / 6G | 只跑 Windows 专属的应用 |
| ser-mac | macOS 15（黑苹果） | 8 核 / 8G | 给 Agent 用 |

Docker 那台搬过去之后，之前给 hy2 配的那个"伴生"容器也直接删掉了。Linux 上 UDP 端口是内核直接转发的，原来的问题根本就不存在了。

Windows 这次装的是 Server 版，没有装 Windows 11。Server 版没那么多花里胡哨的东西，系统更新也能自己控制，拿来跑几个常驻应用更合适。装的时候有个小坑：PVE 给虚拟机的是 VirtIO 虚拟硬盘，Windows 安装程序不认识，一开始一块盘都看不到，要先手动加载 VirtIO 驱动才行。

![20-winserver-no-disk](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095307993.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Windows Server 安装程序找不到硬盘，要先加载 VirtIO 驱动</center><br>

![22-winserver-autologon](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095304834.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>用 Sysinternals 的 Autologon 设置开机自动登录</center><br>

最后顺手装了一台黑苹果。显卡没办法直通，也驱动不起来，所以界面全靠 CPU 软件渲染，用起来还是有点卡。但这台机器的 CPU 还不错，不跑图形任务的话，只靠 CPU 硬扛，大部分的编译和网页浏览其实都能完成。**拿来给 Agent 用是完全够的。**

![QQ_1791036590133](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003090959062.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>跑在 PVE 上的黑苹果</center><br>

我自己日常用的 Mac 性能已经足够强了，所以分工很简单：编译、iOS 开发、图形类的任务在本地 Mac 上做；网页浏览这类杂活，就交给 Agent 去操控那台黑苹果。两边互不打扰，我的电脑也不用让给 Agent。

## 后言

折腾了这么多年，Hyper-V、WSL2、Windows Docker 都试过一遍，最后发现问题不在方案，而在宿主机。宿主机换成 PVE 之后，Windows 退回到它真正擅长的位置，就是一台跑 Windows 应用的虚拟机，其他服务回到 Linux 上原生跑。
