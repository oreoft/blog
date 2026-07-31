---
layout: post
title: 写了个 IDEA 插件，把项目里的 REST 接口都拍平摆在一个面板里
excerpt: 大仓库里接口一多就靠猜，全局搜索还搜不了完整路径，干脆自己写一个
category: tools
keywords: idea, plugin, restful, kotlin, fastapi
lang: zh
---

## 前言

以前写别的语言的时候就用过这类接口浏览插件，一直觉得挺好用的。项目一旦做大了，接口这东西是真的多，新老接口混在一起，光凭记忆去代码里翻根本翻不过来——尤其是那种大仓库，你可能只隐约记得这个接口跟 user 相关，具体叫什么、在哪个类里，完全靠猜，很难精确定位。

IDE 自带的全局搜索其实也帮不上太大忙，因为接口路径里的 `/` 很容易被当成分隔符处理，没法拿一整段做连续匹配。最典型的场景是从 Chrome 的 Network 面板里直接复制一个完整接口路径，比如 `/api/v1/user/detail/list`，往全局搜索框里一贴，根本搜不出东西，只能把这段路径拆开一个词一个词去试，很不方便。这个对后端同学尤其致命——接口是整条数据链路的入口，从这里进来，一路往下追到 Service、Repository，最后落到 DB，看的就是这条完整链路，入口都找不准，后面全白搭。

真正让我下决心自己写一个的是另外几件事。第一是随着 IDEA 版本不停更新，之前用得好好的那几个插件陆续都不兼容了，隔一段时间就要重新去找替代品，这个折腾本身就很烦。第二是找替代品的过程中翻了不少同类插件，发现里面塞了一堆用不上的臃肿功能——倒不是说这些功能不好，别人的产品思路我理解也尊重，只是不是我要的东西。第三，也是最直接的一个：最近 Python 写得越来越多，翻遍市面上这类插件，几乎清一色只认 Java 系框架的 Controller 注解，FastAPI 完全没人管，可后端用 Python 写接口这个量一点不比 Java 少。

于是干脆自己写一个，先把 Java 系框架和 FastAPI 都覆盖上，尽量守住"只做接口浏览+跳转"这一个单一职责，不去堆砌用不上的功能。如果有其他语言/框架的诉求，欢迎直接提 PR，大家一起测一起把这块拼图补全。

## 正文

### 先划清楚这一版做什么、不做什么

翻了下 RestfulBox 的截图，发现它野心更大一点，还带了发请求、看返回结果的面板，有点 Postman 内嵌进 IDE 的意思。这个我没打算跟——一是这块功能复杂度不低，二是发请求这事本来就有专门的工具在做，没必要在 IDE 插件里重造一遍，也正好符合前面说的不想做臃肿的想法。这一版就死磕**浏览 + 跳转**这一个场景：扫出所有接口，选中一个直接跳到代码里，够了。

### 架构：一个扩展点吃遍四种框架

核心是抽了一个 `ApiParserContributor` 扩展点接口，每种框架各自实现一个：

```kotlin
interface ApiParserContributor {
    fun collect(project: Project, scope: GlobalSearchScope): List<ApiEndpoint>
}
```

Spring、JAX-RS、Micronaut 这几个 Java 系框架的注解识别逻辑，没有从零造轮子——直接**移植改造自 RestfulHelper**（MIT 协议开源），包括它那套处理字符串拼接、常量引用的健壮值提取逻辑，改造之后统一适配成本项目自己的 `ApiEndpoint` 模型，licence 和署名都在 NOTICE 里保留好了。FastAPI 这块是新写的，基于 Python PSI 去解析 `@app.get(...)`、`APIRouter(prefix=...)` 和 `include_router` 的路径拼接。

Python 支持这块用了一个小技巧：`plugin.xml` 里用 `<depends optional="true">com.intellij.modules.python</depends>` 声明依赖，这样没装 JetBrains 官方 Python 插件的用户，装这个插件也不会报错，就是看不到 FastAPI 的接口而已，其余框架照常工作。

UI 这层完全不关心接口是哪个框架来的，只认 `List<ApiEndpoint>`，工具窗口里可以按路径前缀、方法、文件/类、模块四个维度切换分组，还有个搜索框实时过滤。

### 踩的一个坑：全量扫描堵死了 UI 线程

开发过程里冒出来一个挺典型的 IDEA 插件坑：一开始筛选框每敲一个字，是直接同步调用所有 parser contributor 重新跑一遍全项目扫描，然后在 EDT（UI 主线程）上等结果。项目小的时候感觉不出来，一旦接口数量上去了，输入的时候界面直接卡一下，体验很差，本质上是把重的索引访问放到了不该放的线程上。

后来改成了非阻塞的异步刷新：项目扫描结果统一缓存在一个 project 级的 service 里，PSI 变更时只增量重新扫受影响的文件而不是全量重扫，搜索和切换分组都只在内存里的缓存快照上做，不再碰索引。顺手还发现并修了个关联的小问题——刷新失败或者被取消的时候，缓存状态之前会被错误地标记成"干净"，导致该重扫的时候反而不重扫了。

### 全局跳转和设置页

除了工具窗口里的树状列表，还做了一个全局快捷键（`Cmd+Option+\` / `Ctrl+\`）唤起的模糊搜索弹窗，输入路径片段或者方法名就能直接定位并跳转，不用先手动点开工具窗口再去找。

这里也有个小坑：不同操作系统、不同用户自定义的 Keymap，实际生效的快捷键都可能不一样，如果写死一个提示文案是会误导人的。所以做了个专门的设置页（`Settings → Tools → RestfulController`），读的是当前生效的 Keymap，展示的是用户实际能按出来的那个快捷键，而不是一个写死的默认值；页面上还能直接改快捷键、调整弹窗是出现在屏幕正中间还是跟着鼠标走，改完直接写回 IDE 自己的 Keymap，跟 `Settings → Keymap` 里看到的是同一份数据，不会出现插件自己存一份、跟系统不一致的情况。

![QQ_1785469273949](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260730224122359.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>设置页读取当前生效的 Keymap，展示的是用户实际能按出来的快捷键，弹窗位置也能在这调</center><br>

![QQ_1785469467685](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260730224437712.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>工具窗口里所有接口按选定的维度分组展示，支持实时搜索过滤</center><br>

![QQ_1785469500004](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260730224506053.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>全局快捷键唤起模糊搜索，输完路径片段直接回车跳到对应的处理方法</center><br>

### 开发过程：写着写着换了个人接着写

这个插件是彻底靠 AI 辅助写完的，而且中间还接力换过几次"人"。最早是拿另一个 AI 编程工具起的头，定了设计和第一版实现；写到一半那边的 session 上下文用得差不多了，我就把交接的会话记录甩给 Claude 接着写，Claude 又往前推了一大截——四个框架的解析器、工具窗口、全局搜索这些主体功能基本都是这段搞定的。结果写着写着 Claude 这边的 token 也到期了，干脆又换成 Codex 接着收尾，把设置页、异步刷新、快捷键这些体验细节补完，顺手还做了一遍性能和架构的自查（就是上面那个 EDT 卡顿的坑，是这一轮自查出来的）。

一开始还担心几个不同的 AI 接力写同一个项目会不会写出风格割裂的代码，实际做下来发现问题不大——只要设计文档和实现计划留得足够清楚，交接的时候把这些文档甩过去，新接手的 AI 很快就能对齐上下文继续干活，人在中间主要是把控方向、跑测试、抓一下明显不对劲的地方。

## 后言

现在插件已经跑起来了，代码开源在 [github.com/oreoft/restful-controller](https://github.com/oreoft/restful-controller)。整体感受是，做一个覆盖多框架的 IDE 小工具，难点其实不在某一个框架的解析细节上（这块很多都能从开源项目里借鉴），而在于把扩展点设计得足够干净——新增一个框架不该动到 UI 和其他解析器的代码。这一点这次算是拿捏住了。

后续应该还会根据自己实际用的时候踩到的别扭点慢慢打磨，暂时没有再往"发请求"这个方向去扩的打算，浏览加跳转这个场景对我来说已经解决了最烦的那个问题。至于其他语言的支持，还是那句话，等你的 PR。
