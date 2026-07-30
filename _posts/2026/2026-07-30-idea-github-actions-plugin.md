---
layout: post
title: 写了个 IDEA 插件，把 GitHub Actions 塞进了 Git 面板
excerpt: 每次为了看一眼 Action 跑没跑成都要切出去开浏览器，干脆自己写一个得了
category: tools
keywords: idea, plugin, github actions, kotlin
lang: zh
---

## 前言

平时开发的时候，GitHub Actions 用得挺多的，CI、部署、跑个定时任务基本都靠它。但有个事一直挺烦的：不管是提了个 PR 想看看 CI 跑没跑过，还是想手动补跑一次部署，都得从 IDEA 里切出去，打开浏览器，找到仓库，点到 Actions 标签页，再一层层点进去看。人本来就在写代码的心流里，这一下切出去，回来就得重新找状态。

我就寻思这么个高频操作，IDE 里应该有更顺手的办法。调研了一圈发现两条路都不太行：

- IDEA 自带的 GitHub 集成，能看 PR、看 Git Log，也能看某次 commit 对应的 Actions 状态，但**只能看**，没法手动触发 `workflow_dispatch`。
- 市面上有个叫 GitHub Actions Manager 的插件，功能是全的，能触发能看日志，但**部分功能是收费的**。

一个不支持执行，一个收费，那干脆自己写一个得了，核心功能其实也不复杂。而且我想了一下，与其单独开一个新的工具窗口，不如直接**塞进 IDEA 已有的 Git 面板**里，跟 Log、Console 这些 tab 平级放一个 "GitHub Actions" tab。这样不管是看 Git 记录还是看 Action 状态，都在同一个地方，不用来回切窗口。

## 正文

### 往 Git 面板里塞一个 tab，靠谱吗

一开始我也没底，这属于往人家(git4idea 插件)地盘里插东西。翻了下 IntelliJ Platform 的源码才发现，Git 面板里的 Log / Console / Worktrees 这几个 tab，本来就是通过一个叫 `changesViewContent` 的扩展点注册进去的，不是什么私有实现。也就是说第三方插件完全可以用同样的方式，往这个面板里加一个自己的 tab，跟官方 tab 平起平坐。这个方案定下来之后心里就有底了，剩下就是把内容填进去的事。

### Token 这块，绕了一个小弯路

最开始设计的时候，很自然地想到要让用户自己去 GitHub 生成一个 Personal Access Token，然后填到插件的设置里。但转念一想，这个体验其实挺糟心的——用户本来就已经在 IDEA 里登录了 GitHub 账号(Settings → Version Control → GitHub)，为什么还要让人家再单独生成一遍 Token，再复制粘贴一遍？

翻了下 IDEA 自带 GitHub 插件的源码，发现账号和 Token 都是通过 `GHAccountManager` 统一管理的，Token 本身存在系统的 Password Safe 里，插件直接拿现成的账号去读就行，完全不用自己再存一份。于是把这块方案改成了**直接复用 IDEA 已登录的 GitHub 账号**，用户啥都不用配，装完插件打开一个有 GitHub 远程仓库的项目，就能直接用了。这个决定算是这个插件里我最满意的一处设计。

### 功能长什么样

核心链路就是：识别当前项目的 GitHub 仓库 → 列出所有 workflow → 选中一个看它最近的运行记录 → 双击进去看具体是哪个 job 挂了、日志里写了啥 → 需要的话手动点一下触发。

![QQ_1785447684367](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260730164133340.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>左边是仓库下所有 workflow，选中一个右边就是它最近的运行记录，带状态图标</center><br>

双击某一次运行记录，会切到详情视图，能看到这次跑了哪些 job，每个 job 展开就是完整日志，不用再跳去网页上翻。

![QQ_1785447713337](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260730164158122.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>双击进入 job 详情，日志直接在 IDE 里看，报错了也不用切浏览器去找</center><br>

最核心的那个诉求——手动触发，也做了，点一下工具栏的触发按钮，输入要跑的分支(默认帮你填好当前分支)，直接就发出去了，几秒钟后回来刷新一下就能看到新的一条记录。

![QQ_1785447728519](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260730164214013.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>点一下就能手动触发 workflow_dispatch，分支默认识别当前项目的分支</center><br>

### 开发过程

这次开发过程挺有意思的，不是我一个人从头怼到尾。想法定下来之后，先跟 AI 过了一遍设计——面板放哪、账号怎么复用、接口怎么调，一步步聊清楚了再动手，中间还专门去翻了 IntelliJ Platform 的源码核实一些关键 API 是不是真的存在（比如 `changesViewContent` 这个扩展点，`GHAccountManager` 的具体用法），免得写出来的东西全靠猜。空壳先跑起来看了眼位置和样式对不对，确认没问题之后，剩下的核心功能就交给另一个 AI 一口气写完了，我这边主要是review 代码、挑 bug、把一些边界情况（比如企业版 GitHub、账号 Token 失效之类）修一下。人和 AI 各干各擅长的部分，效率确实高了不少。

## 后言

现在这个插件已经开发完、上架了，代码也是开源的，仓库在 [github.com/oreoft/github-actions-controller](https://github.com/oreoft/github-actions-controller)，感兴趣的可以直接去看源码或者提 issue。后续打算继续慢慢维护，比如加上 workflow YAML 里 `inputs` 的动态表单、多账号切换这些还没来得及做完善的地方。

说到底这就是个很小的痛点驱动出来的东西——不是什么了不得的大工程，就是觉得这个操作重复得太多次了，顺手解决掉，用起来是真的顺手了不少。
