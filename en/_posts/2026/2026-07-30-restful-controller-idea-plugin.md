---
category: tools
excerpt: Once a monorepo has too many APIs, you’re basically guessing; global search
  can’t even find the full path, so I just wrote my own.
keywords: idea, plugin, restful, kotlin, fastapi
lang: en
layout: post
title: I Built an IntelliJ IDEA Plugin That Flattens All the REST APIs in a Project
  into a Single Panel
---

## Preface

Back when I was writing in other languages, I’d already used this kind of “API browsing” plugin, and I always found it pretty handy. Once a project gets big, you *really* end up with a ton of endpoints. Old and new APIs get mixed together, and trying to dig them out of the codebase purely by memory is basically impossible—especially in a huge monorepo. You might vaguely remember “this one is user-related,” but what it’s called and which class it lives in? Total guesswork, and it’s hard to pinpoint precisely.

The IDE’s built-in global search doesn’t help that much either, because the `/` in an endpoint path is easily treated as a separator, so you can’t do a continuous match on the whole string. The most typical scenario: you copy a full path straight from Chrome DevTools’ Network panel, like `/api/v1/user/detail/list`, paste it into global search, and… nothing. You’re forced to split the path and try word by word, which is super annoying. This is especially deadly for backend folks—an API endpoint is the entry point of the entire data chain. From there you trace down through Service, Repository, and finally to the DB. You’re following that *full* chain; if you can’t even locate the entry point, everything after that is pointless.

What really pushed me to write my own was a few other things. First: as IDEA keeps updating, the plugins I used to rely on gradually became incompatible. Every so often I had to go hunt for replacements, and that hassle alone is irritating. Second: while looking for alternatives, I tried a bunch of similar plugins and found they were stuffed with bloated features I didn’t need—not that those features are bad; I get and respect other people’s product thinking. It’s just not what I want. Third, and most directly: lately I’ve been writing more and more Python. I searched the market for this category of plugin and almost all of them only recognize Java-framework Controller annotations. FastAPI? Nobody cares. But the amount of backend APIs written in Python is absolutely not less than Java.

So I just wrote one myself: cover both the Java ecosystem frameworks and FastAPI first, and stick as hard as possible to a single responsibility—“API browsing + navigation”—without piling on features I don’t use. If you need other languages/frameworks, feel free to open a PR. Let’s test together and fill in this puzzle piece by piece.

## Main

### First, draw a clear line: what this version does and doesn’t do

I took a look at RestfulBox screenshots and realized it’s a bit more ambitious: it even has panels for sending requests and viewing responses—kind of like embedding Postman into the IDE. I’m not planning to follow that path—first, that feature set isn’t trivial in complexity; second, there are already dedicated tools for sending requests, so there’s no need to reinvent it inside an IDE plugin. It also aligns with the “don’t be bloated” idea I mentioned earlier. This version is going all-in on one scenario: **browse + navigate**. Scan all endpoints, select one, jump straight to the code. That’s enough.

### Architecture: one extension point to cover four frameworks

The core is an extracted extension point interface, `ApiParserContributor`, with one implementation per framework:

```kotlin
interface ApiParserContributor {
    fun collect(project: Project, scope: GlobalSearchScope): List<ApiEndpoint>
}
```

For the annotation recognition logic of Java frameworks like Spring, JAX-RS, and Micronaut, I didn’t reinvent the wheel—this is directly **ported and adapted from RestfulHelper** (MIT-licensed open source), including its robust value-extraction logic for handling string concatenation and constant references. After the adaptation, everything is unified to fit this project’s own `ApiEndpoint` model, and the license and attribution are properly preserved in NOTICE. The FastAPI part is newly written, based on Python PSI to parse path composition across `@app.get(...)`, `APIRouter(prefix=...)`, and `include_router`.

For Python support I used a small trick: in `plugin.xml`, declare an optional dependency with `<depends optional="true">com.intellij.modules.python</depends>`. That way, users who don’t have JetBrains’ official Python plugin installed can still install this plugin without errors—they just won’t see FastAPI endpoints. Everything else works as usual.

The UI layer doesn’t care which framework an endpoint comes from; it only consumes `List<ApiEndpoint>`. In the tool window, you can switch grouping across four dimensions: path prefix, method, file/class, and module. There’s also a search box for real-time filtering.

### One pitfall: full scans blocking the UI thread

During development I ran into a pretty classic IDEA plugin pitfall: at first, every keystroke in the filter box would synchronously call all parser contributors to rescan the entire project, and then wait for results on the EDT (the UI main thread). On small projects you don’t notice it, but once the number of endpoints grows, the UI freezes on input and the experience is awful. Fundamentally, I was doing heavy index access on the wrong thread.

Later I switched to non-blocking async refresh: scan results are cached in a project-level service; when PSI changes, only the affected files are rescanned incrementally instead of doing a full rescan; searching and switching groupings operate only on an in-memory snapshot of the cache and no longer touch the index. Along the way I also found and fixed a related issue—when refresh failed or got canceled, the cache state used to be incorrectly marked as “clean,” which caused it to *not* rescan when it actually should have.

### Global navigation and the settings page

Besides the tree list in the tool window, I also added a global hotkey (`Cmd+Option+\` / `Ctrl+\`) to bring up a fuzzy-search popup. Type a path fragment or method name and you can locate and jump directly—no need to manually open the tool window first and then hunt around.

There’s a small pitfall here too: across different OSes and user-customized keymaps, the actual effective shortcut can vary. If you hardcode a hint string, you’ll mislead people. So I built a dedicated settings page (`Settings → Tools → RestfulController`) that reads the currently active keymap and displays the shortcut the user can actually press, rather than a hardcoded default. On that page you can also change the shortcut directly, and adjust whether the popup appears centered on the screen or follows the mouse. After changes, it writes back into the IDE’s own keymap—the same data you see under `Settings → Keymap`—so there’s no “plugin stores its own copy and gets out of sync with the system” situation.

![QQ_1785469273949](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260730224122359.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>The settings page reads the currently active Keymap and shows the shortcut the user can actually press; you can also adjust the popup position here</center><br>

![QQ_1785469467685](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260730224437712.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>All endpoints in the tool window are grouped by the selected dimension, with real-time search filtering</center><br>

![QQ_1785469500004](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260730224506053.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Fuzzy search triggered by the global shortcut—enter a path fragment and press Enter to jump to the corresponding handler method</center><br>

### Development story: I kept writing, then “someone else” took over and kept writing

This plugin was completed entirely with AI assistance, and in the middle I even swapped “people” a few times in a relay. At the very beginning I used another AI coding tool to kick things off, set the design, and build the first implementation. Halfway through, that tool’s session context was basically used up, so I dumped the handoff chat logs to Claude and had it continue. Claude pushed it forward a lot—the main features like the four framework parsers, the tool window, and global search were largely done in that phase. Then, as I kept going, Claude’s token budget expired too, so I switched to Codex to finish it off: the settings page, async refresh, shortcuts, and other UX details. I also did a round of performance and architecture self-check (the EDT-freeze pitfall above was found during this round).

At first I worried that having multiple different AIs take turns writing the same project would produce stylistically fragmented code. In practice it wasn’t a big problem—as long as the design docs and implementation plan are clear enough, and you hand those docs over during the transition, the new AI can align context quickly and keep moving. The human in the loop mainly steers direction, runs tests, and catches the obviously wrong bits.

## Afterword

The plugin is now up and running, and the code is open-sourced at [github.com/oreoft/restful-controller](https://github.com/oreoft/restful-controller). Overall, my takeaway is: for a multi-framework IDE utility like this, the hard part isn’t the parsing details of any single framework (a lot of that can be learned from open source), but designing the extension point cleanly enough—adding a new framework shouldn’t require touching the UI or other parsers. This time, I think I nailed that.

Going forward I’ll probably keep polishing it based on the little annoyances I hit in real use. For now I don’t plan to expand toward “sending requests”—for me, browsing plus navigation already solves the most painful problem. As for support for other languages: same line as before, I’m waiting for your PR.