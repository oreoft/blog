---
category: other
excerpt: Replace the cooling fan on what I consider the best mini PC in the Eastern
  Hemisphere
keywords: other, macos
lang: en
layout: post
title: 'DeskMini H470: My Experience Replacing the Cooler with an AXP90'
---

## Preface

I’ve actually been wanting to swap an i9 into my DeskMini H470 mini PC for a long time. After weighing it up, I felt the 10900 ES version was the best choice: on one hand, ES chips are cheaper; on the other hand, with the space constraints of a mini PC, an overly high TDP might be hard to handle. I don’t game—what I’m really craving is simply 10th-gen’s 10 cores / 20 threads and 20MB of L3 cache. Overclocking and 5GHz boost aren’t that important to me, and the ES version fits my needs perfectly. Once I’d decided, the very first step was obviously to upgrade the cooling.

The DeskMini H470’s **height is `46mm`**, so I wanted to pick the best-performing cooler possible within that limit—after all, I’m trying to tame an i9. In the end, I narrowed it down to these two:

![image-20211127192256453](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20230717133927.png)

<center>Noctua NH-L9i CPU Cooler 37mm</center>

![image-20211127192405320](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20230717134015.png)

<center>Thermalright AXP90-X47 FULL 47mm (Full Copper)</center>

I read a bunch of posts, and more people seem to use the Noctua L9i because its height is a perfect fit, and Noctua fans are famous for having the best balance between cooling and noise. I originally planned to go with it too, but it’s **37mm** tall, which felt like **10mm** of wasted headroom—would be nice if I could actually use that space. So I shifted my attention to the Thermalright AXP90, but it’s the opposite extreme: it’s **47mm**, which is `1mm` taller than my DeskMini H470 case height. I wasn’t sure whether that `1mm` tolerance could still work. I dug through basically every post I could find, and the conclusion was: **it fits, but you need to adjust things**. Huge thanks to [this article](https://post.smzdm.com/p/adwn6kqz/)—it was probably the only post on the entire internet about putting an AXP90 on a DeskMini H470 (now it’s one of two 😂).

So here’s my own experience swapping in the AXP90 on a DeskMini H470, for anyone considering the same thing. I’ll give the conclusion first: yes, it fits, but it’s a bit tight—still, it works perfectly. If you want to run a `10070` or `10900` in a DeskMini H470, just pick the AXP90 without thinking twice.



## Unboxing

![image-20211127205843165](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171430947.webp)

<center>Packaging</center><br>

![image-20211127210310681](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171430434.webp)

<center>What’s inside the box</center><br>

![image-20211127210326960](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171429468.webp)

<center>Main unit</center><br>

![image-20211127210605967](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171427060.webp)

![image-20211127210357010](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211127210357.png)

<center>Four heatpipes + backplate mounting kit</center><br>

![image-20211127210431749](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171430604.webp)

<center>Also includes a 5g tube of TF7 (69 RMB on JD.com)</center>



## Disassembly

![image-20211127210632447](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171430908.webp)

<center>Remove all the screws on the back</center><br>

![image-20211127210704273](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432980.webp)

<center>After removing them, pull the small handle to open</center><br>

![image-20211127210748157](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432956.webp)

<center>
  After pulling it out, disconnect the power button cable and separate the chassis from the motherboard
</center><br>

![image-20211127210851572](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432558.webp)

<center>
  If you have a SATA drive connected, disconnect it first, because you need to separate the motherboard from this tray<br>
</center>

![image-20211127210946233](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432896.webp)

<center>Remove the four corner mounting screws</center><br>

![image-20211127211050403](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432637.webp)

<center>Separate the motherboard from the tray—now you can see the back of the motherboard</center><br>

![image-20211127211129829](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432875.webp)

<center>There’s a hidden M.2 slot on the back (only usable with 11th-gen PCIe 4.0)</center>



## Remove the old fan

![image-20211127211242656](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432432.webp)

<center>
  Disconnect the fan power first
</center><br>

![image-20211127211352748](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432359.webp)

<center>
  Twist this latch mechanism so the plastic pins pop out of the motherboard
</center><br>

![image-20211127211447414](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432971.webp)

<center>
  Be a bit careful, then pull firmly and the cooler will come off
</center><br>

![image-20211127211524639](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432215.webp)

<center>
  Old cooler (Intel stock boxed cooler)
</center><br>

![image-20211127211605510](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433878.webp)

<center>
  Thermal paste imprint left on the CPU after removing the cooler
</center>



## Install the new AXP90

![image-20211127211754631](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433998.webp)

<center>
  Peel off the film (super important—leaving it on will seriously hurt cooling performance)
</center><br>

![image-20211127211841539](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433402.webp)

<center>
  Use the included TF7 and apply thermal paste in an X pattern (I recommend the X method)
</center><br>

![image-20211127212028885](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433604.webp)

![image-20211127212112804](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433629.webp)

<center>
  Then place the heatsink body on top
</center><br>

![image-20211127212127581](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433281.webp)

<center>
  Carefully flip it over, then put on the backplate
</center><br>

**Attention attention attention!!!**

![image-20211127212210597](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433787.webp)

![image-20211127212337970](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433744.webp)

<center>
  There are two sizes of these nuts. Mine came pre-installed with the short ones by default, but the short ones are NOT suitable for the DeskMini H470—it won’t leave enough clearance and will press against the motherboard. Remember: you MUST swap them out.
</center><br>

![image-20211127212453081](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433533.webp)

<center>
  Finally, connect the fan power
</center>



## Post-install tweaks

![image-20211127212539374](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433995.webp)

![image-20211127212629336](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433134.webp)

<center>
  When assembling the motherboard tray and motherboard, the red-marked area will push against the motherboard and may cause it to bend (not “may”—it definitely will). So don’t tighten it down too hard; just tighten enough so it’s secure and doesn’t wobble.
</center><br>

![image-20211127212732895](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433264.webp)

<center>
  My solution for the motherboard bending: 1) don’t fully crank it down; 2) bend the backplate slightly to make room for the protruding screws on the motherboard.
</center><br>

![image-20211127212912555](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433631.webp)

<center>
  The final look is pretty nice
</center><br>

![image-20211127212944215](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434247.webp)

<center>
  Reconnect the power button cable
</center>



## The 1mm problem and how I solved it

![image-20211127213142498](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434843.webp)

![image-20211127213544052](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434708.webp)

<center>
  The problem showed up when putting it back in—I found it got stuck and wouldn’t go in.
</center><br>

![image-20211127213611188](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434586.webp)

<center>
  It was catching here, so I decided to remove this screw and flex that tab outward a bit
</center><br>

![image-20211127213724207](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434886.webp)

<center>
  After removing the screw, I found there was actually a lot of extra clearance here
</center><br>

![image-20211127213830029](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434489.webp)

<center>So I just pushed it in smoothly. Then I checked and realized this screw can’t really be tightened back in. And since I’ll probably upgrade the CPU or other parts later anyway, there’s no need to force it back—everything is still relatively secure structurally. Losing these two screws doesn’t really make a difference. Stability is excellent, the mesh doesn’t hit the fan, and overall I’m very satisfied.</center><br>

![image-20211127214019244](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434875.webp)

<center>Because the height is 1mm taller, the screw can’t be tightened, and the fan bulges out just a tiny bit—but it doesn’t affect usage.</center>



## Closing thoughts

![image-20211127215952591](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211127215952.png)

<center>Left is before the swap, right is after</center>

A picture is worth a thousand words—I don’t need to say much more about what to do. It’s genuinely impressive. This lays a solid foundation for cooling a 10900 ES and gives me confidence. After using it for a while, if the timing is right, I’ll pick up a 10900 ES and finally experience what 10C20T feels like.

One downside of the AXP is that it’s too loud. I looked into it and found the AXP90’s minimum fan speed is 1600rpm—so even at 30+ °C it still runs at 1600rpm. So you’ll want to tweak the fan curve in BIOS: keep it quiet under light loads, and let it rip under heavy loads.

![image-20211127215158225](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434411.webp)

<center>At first I set it to Silent mode, but I found the minimum was still 1600rpm</center><br>

![IMG_5160](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434474.webp)

<center>
  You have to set it to Custom—this is my configuration in the screenshot
</center>