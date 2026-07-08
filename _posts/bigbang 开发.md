---
layout: post
title: MacOS自定义快捷键一键休眠
excerpt: 找了很久终于找到优雅的方式了
category: other
keywords: other, macos
---

## 前言

参考资料

刚开始半屏通知

![download-8](/Users/oreoft/Downloads/download-9.png)


然后实现了交互
![Simulator Screenshot - iPhone 17 Pro - 2026-01-19 at 15.05.37](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260119231300279.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

不支持动画



然后实现了

https://developer.apple.com/documentation/appintents/appintent



![2026-01-19 17.09.36](/Users/oreoft/Desktop/2026-01-19 17.09.36.gif)



支持动画，但是最低 ios26

https://developer.apple.com/documentation/appintents/snippetintent

![download-6](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260119231209231.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

![download-5](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260119231142711.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)



好不容易网页的细节调好了
![image-20260119231809736](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260119231809771.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

- 您说得对，我确实查了一下：**Snippet View (片段)** 对交互限制极大，特别是复杂的 

  ```
  WKWebView
  ```

   触摸和滚动，很可能也是“只能看不能动”，甚至也被禁掉 JS。

  

  我们目前陷入了死循环：

  1. **Quick Look** + 文件 URL = ❌ 禁 JS (白屏/无交互)
  2. **Show Web Page** + Data URI = ❌ 不支持 Scheme (您刚才的报错)
  3. **Intents Snippet** = ❌ 交互受限/不支持动画![download-3](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260119231130422.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)





# TinyBang: 千次被拒的开发血泪史

> "我只想要不打开 App 就能跑一段 JS 而已，为什么这么难？" —— 一个 iOS 开发者的叹息

## 🎯 最初的目标

我们要实现一个类似 "锤子大爆炸 (Big Bang)" 的分词工具，核心诉求只有四点：

1. **高交互性**: 需要复杂的文字流式布局和动画 (原生 Text 组件做不到，必须上 Web 技术)。
2. **不跳 App (Overlay)**: 必须以模态窗口 (Modal) 形式悬浮在当前 App 上方。
3. **一键直达**: 通过 Shortcuts (快捷指令) 一步唤醒。
4. **纯离线**: 保护隐私，且零延迟。

------

## 🪦 尝试过的死胡同 (失败记录)

### 1. Intent + "快速查看" (Quick Look) + 本地 HTML

**思路**: Swift 生成一个本地文件 `file:///tmp/tinybang.html`，然后用捷径的 "快速查看" 动作打开。 **结果**: ❌ **失败** **原因**: iOS 的 `Quick Look` 虽然能渲染 HTML，但出于安全考虑，**强制禁用了本地文件的 JavaScript 执行**。页面能显示，但完全是死的，无法交互。

### 2. Intent + "显示网页" (Show Web View) + Data URI

**思路**: Swift 将 HTML 压成 Base64 字符串 (`data:text/html;base64,...`)，喂给 "显示网页" 动作。 **结果**: ❌ **失败** **原因**: "显示网页" (底层是 Safari) **不支持非 HTTP 协议**。它直接报错 "Unsupported URL"，拒绝渲染 Data URI。

### 3. Intent + "显示网页" (Show Web View) + 本地文件

**思路**: 同方案 1，但换成 "显示网页" 动作。 **结果**: ❌ **失败** **原因**: 同上，Safari 视 `file://` 协议为安全隐患，拒绝加载或者拒绝执行其中的 JS 脚本。

### 4. 原生 App Intent (纯原生 UI)

**思路**: 不使用 Web View，直接用 SwiftUI 编写分词界面，通过 Intent 返回。 **结果**: ❌ **效果差** **原因**: SwiftUI 的 Text 组件虽然能显示，但 **不支持复杂的流式动画 (Flow Layout Animations)**。原生 UI 在处理“文字爆炸”这种高频位置变动时，动画效果远不如 CSS 的 `transition` 灵动，且手势交互受限。

### 5. Intent Snippet (App Intents via SwiftUI)

**思路**: 使用 iOS 17+ 的 `ShowsSnippetView` 返回一个嵌入式视图。 **结果**: ❌ **版本不支持 / 不稳定** **原因**: 这个 API 对系统版本要求极高（需要最新的 iOS 18/26 Beta 环境），且在当前环境下极不稳定，经常无法加载或加载后触摸事件失效。我们尝试调研后发现目前无法用于生产环境。

### 5. URL Scheme (`instash://tinybang`)

**思路**: 捷径直接打开一个 App 的自定义链接。 **结果**: ⚠️ **体验不达标** **原因**: 这会导致 **App 强制跳转**。用户会从当前 App (如微信) 瞬间跳到我们的 App，破坏了“沉浸式/不打扰”的核心体验。

### 6. Action Extension (系统分享菜单)

**思路**: 开发一个原生的 iOS Action Extension，通过系统 "分享" 按钮唤出。 **结果**: ⚠️ **路径过长** **原因**: 技术上最可行（原生 UI、支持 JS），但**操作路径太长**：选文字 -> 点分享 -> 找图标 -> 点击。用户觉得比起“一键捷径”，这太麻烦了。

### 7. 捷径 "与 App 共享 (Share with App)"

**思路**: 试图用捷径的 "与 App 共享" 动作直接把数据传给插件。 **结果**: ❌ **失败** **原因**: 该动作只支持传给 **主 App**，无法传给 **Extension**。我们的插件在列表里是不可见的。

### 8. Cloud Runner (云端运行，被否定)

**思路**: 捷径打开一个我们部署的 `https://tinybang.app`。 **结果**: ❌ **被否决** **原因**: 违反了 **"纯离线"** 的原则。

------

## 🔮 最后的希望：绝地求生

我们被 iOS 的沙箱机制逼到了墙角：

- **离线 + JS** = 被 Quick Look 封杀。
- **离线 + Web View** = 被协议检查 (`file://`, `data:`) 封杀。
- **原生插件** = 被操作路径劝退。

### 最后的疯狂想法：Localhost Server (本地服务器)

既然 Safari 只认 `http://`，那我们就给它一个 `http://`。 **思路**:

1. App 在手机后台静默启动一个微型 HTTP 服务器 (`localhost:8080`)。

2. 捷径访问 `http://localhost:8080`。

3. **Safari 以为这是网络请求**，所以 JS 全开；**但数据其实就在本地**，既离线又安全。

4. ⚠️ 真正的致命风险 (Showstopper)
   虽然前面都很好，但有一个巨大的隐患：

   iOS 的沙箱网络隔离 (Sandboxing)

   场景：主 App (后台进程) 跑 Server，捷径 (Safari进程) 访问 localhost。
   风险：iOS 内核可能会禁止两个不同进程通过 localhost 通信。
   有时候能通 (看系统版本)。
   有时候不通 (Safari 显示无法连接服务器)。
   结论

   好消息是，SFSafariViewController (捷径的显示网页)：它就是一个独立进程的 Safari 浏览器。只要您的主 App 在后台跑了一个服务器，且监听的是 localhost，Safari 是可以通过回环地址 (127.0.0.1) 访问到的。这不违反沙箱规则（因为这是 TCP/IP 层的通信，iOS 允许 App 绑定 >1024 的端口）。

然后现在问题是**关键点**：App 必须在后台“活着”。，解决方案：beginBackgroundTask
我们必须在 Intent 里利用 UIApplication.shared.beginBackgroundTask 申请一段后台运行时间（系统通常允许 30秒 - 3分钟）。这样即使 Intent 返回了，服务器还能在后台坚挺一会儿，足够网页加载完成。

这是理论上唯一能同时满足 **"不跳 App" + "一键捷径" + "完整交互"** 的终极方案。



![image-20260120141349722](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260120141349760.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)







```
graph TD
    A[App 启动/触发更新] --> B{请求 version.json}
    B -->|Local < Remote| C[下载 Zip 包]
    B -->|Local == Remote| D[无操作]
    C --> E[解压到 Temp]
    E --> F[校验 Hash/完整性]
    F -->|成功| G[原子替换 Documents/TinyBang 目录]
    G --> H[更新本地 version 记录]
    H --> I[下次启动生效]
```



```
public static func assembleHTMLString(with text: String, language: String? = nil) -> String? {
    // 1. 定义寻找顺序：先沙盒，后 Bundle
    let updateDir = FileManager.default.urls(for: .documentDirectory, ...).first!.appendingPathComponent("TinyBangLatest")
    let bundle = Bundle.module
    
    // 2. 尝试从沙盒加载 (热更版)
    var htmlContent: String?
    if FileManager.default.fileExists(atPath: updateDir.path) {
        htmlContent = loadFile(from: updateDir, name: "tinybang.html")
        // ... 加载 js/css ...
    }
    
    // 3. 如果沙盒加载失败，回退到 Bundle (保底版)
    if htmlContent == nil {
        htmlContent = bundle.load(...)
    }
    
    // 4. 组装 (逻辑不变)
    return inject(htmlContent, css, js)
}
```



![image-20260120171824998](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260120171825037.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
