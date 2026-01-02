---
category: tools
excerpt: After a long search, I finally found an elegant way to do it.
keywords: other
lang: en
layout: post
title: 'I’m Done for: IntelliJ IDEA’s Postfix Completion Feature'
---

## Preface

Earlier I wrote a post introducing IDEA’s Live Templates (dynamic templates). Honestly, there’s way too much “reference material” online for this—everyone just copies everyone else, not even changing the formatting. If the formatting *is* different, it’s probably because they accidentally lost it while copy-pasting.  

I’ve always had a need: I want `var.sout` + Enter to turn into `System.out.println(var);`. I’ve researched this multiple times. My original approach was wrong—I kept thinking this was a Live Templates feature, but Live Templates can’t put that `var` into `println()` while also keeping `var` in front. I always felt like there must be some built-in trick I didn’t know, so I even went through IDEA’s official docs, reread all the built-in functions for variables again and again, and studied how IDEA’s built-in `sout` works for a long time… and every time I ended up giving up.

Let me give a super simple example. I want to use a Live Template to write a `.test` that implements `sout`.

1. First step: set up a Live Template

![image-20210404183921703](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404183921.png)

<center>Set up a test, and apply it to java-other</center>

2. Then look at the result

   ![2021-04-04 18.38.10](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404183959.gif)

<center>The result is pretty dumb</center>

In the end, I found something in IDEA’s docs called **Postfix Completion**. I searched for it in IDEA and it scared me—turns out the `.var` / `.sout` I’d been dreaming about is right here!!!

![image-20210404184658588](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404184658.png)

<center>It includes most commonly used implementations</center>

After tinkering with it for a while, I want to summarize what I’ve learned: some built-in postfix completions I use a lot, plus a few custom ones I made and want to share.

## IDEA built-in postfix completions I use

- Quickly generate a for loop — `num.fori`

  ![2021-04-04 19.00.47](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191403.gif)

- Quick null check and non-null check — `num.null` & `num.nn`

![2021-04-04 19.15.09](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191701.gif)

- String format concatenation — `string.format`

![2021-04-04 19.16.20](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191918.gif)

- Quick `new` and quick reference generation — `class.new` & `object.var`

![2021-04-04 19.17.40](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191929.gif)

- Quickly wrap code with try/catch — `statement.try`

![2021-04-04 19.18.32](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191935.gif)

- Quick return — `result.return`

![2021-04-04 19.19.03](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191941.gif)

You can probably tell this looks a lot like Live Templates. That’s exactly why I kept looking in the wrong direction before. This is basically Live Templates plus. Notice that most of the time I just type the first few letters and then use completion—once you get used to it, it feels *so* good, and your bug-producing efficiency goes up up 😜

## Custom postfix completions

### Explanation

Everything above is built into IDEA, but we can also write our own. It’s similar to Live Templates, except there’s no concept of groups here—custom ones all get written under Java. My OCD doesn’t love it, but if it boosts efficiency, I’ll live with it.

So how do you write one? The best way is to look at how IDEA’s built-in postfix completions are implemented. I’ll use the `sout` I’d been obsessing over as an example.

![image-20210404192600733](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404192600.png)

The image above is the implementation of `sout`. Following the annotations in the screenshot, here’s what each part means:

1. This is the key, i.e. `.key`, the trigger condition for your postfix completion
2. Applicable JDK version. Some lambda syntax might only be supported in JDK 8, and you can configure that here
3. Applicable types. Usually it’s fine whether you fill this in or not, but specifying it makes it more robust
4. `$EXPR$` means `expr.key`. This is where the `expr` will end up
5. `$END$` is where your cursor will land at the end

----

### Sharing

First: I’m only sharing my ideas. I’m not going to export and share my exact configuration—not because I’m stingy, but because I grind away writing it for ages, and if I just hand it over, everyone’s creativity drops a bit.

- Anyone who’s written Scala knows how nice `toInt`, `toLong`, etc. are for direct casting. But in Java you basically only have `toString()`, and I often don’t dare to use it casually because of NPE. Hutool has a static class `Convert`. Let’s just look at `toStr`:

![image-20210404193838992](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404193839.png)

<center>Introduction to Convert.toStr()</center>

![2021-04-04 19.41.40](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404194439.gif)

<center>My commonly used conversion demo</center>

- Collection null/empty checks. With MyBatis, if no data is found, the ORM returns `null` for objects, but for collections it returns an empty collection. If you check a collection for `null`, there’s a high chance it won’t match your expectations. Sure, collections have `isEmpty()` to quickly check whether there are elements, but relying on that habit isn’t very robust—what if one day the collection itself is `null` and the method doesn’t exist at all, boom NPE... Here’s my postfix approach:

  ![2021-04-04 19.52.08](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404195552.gif)

<center>Demo</center>

## Afterword

There’s actually a lot you can do with this. I really searched for a long time—turns out flipping through the manual more often always brings new discoveries. These days I basically treat IDEA’s manual as English reading material every day: first, it has tons of CS vocabulary, and memorizing more of it will definitely be useful later; second, I personally feel we still haven’t dug deep enough into IDEA. IDEA is powerful—not just something people hype up domestically. There are lots of efficiency-boosting tricks that only a few people might know, waiting for us to explore.

IDEA docs here: [click](https://www.jetbrains.com/help/idea/2021.1/product-educational-tools.html)