---
layout: post
title: DeskMini H470更换AXP90散热经验分享
excerpt: 给我认为东半球最好用的小主机更换散热风扇
category: other
keywords: other, macos, cc
---

## 前言

其实我一直想给自己小主机deskmini-h470换一个i9的处理器。权衡之下我觉得10900es版本最好，一方面es版本价格比较便宜，另外一方面因为小主机空间限制太高的TDP可能顶不住，我不玩游戏我馋的仅仅是十代10核20线程以及20Mb三级缓存。超频和5Ghz睿频其实对于我来说需求不大，es版刚好可以满足我的需求。已经确定好以后，首先第一步肯定是要给我小主机换一个散热。

Deskmini-h470的**高度是`46mm`**，所以我想在范围内尽可能的选择散热能力好一点的，毕竟我要压的可是i9。最终决定在下面两款之间确定

![image-20211127192256453](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20230717133927.png)

<center>猫头鹰（NOCTUA）NH-L9i CPU散热器 37mm </center>

![image-20211127192405320](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20230717134015.png)

<center>利民 AXP90-X47 FULL 47mm 纯铜</center>

我参考了一些帖子，大家用猫头鹰L9i的会多一些，因为它的高度合适，并且猫扇是出了名的散热和噪音平衡的最好。本来我也是选择他，但是他是**37mm**的高度，我感觉冗余了**10mm**，要是能利用起来就好了。所以我又把希望转到了利民XP90上面，但是它也是一个极端，它是**47mm**比我的deskmini-h470的机箱高度多了`1mm`，我不知道这`1mm`的误差是能可以兼容，我翻遍了全网的帖子，得到的结果是**可以放下，但是需要进行调整**。感谢[这篇文章](https://post.smzdm.com/p/adwn6kqz/)，这应该是全网唯一一篇deskmini-h470上上AXP90的帖子(现在是唯二啦😂)。

下面就分享一下我自己DeskMini H470更换AXP90散热器的经验，希望有类似考量的同学可以参考。先说结论吧，可以放但是空间有点挤，不过可以完美发挥作用。如果你也想使用deskmini-h470上`10070`或者`10900`请无脑选AXP90。



## 开箱

![image-20211127205843165](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171430947.webp)

<center>包装</center><br>

![image-20211127210310681](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171430434.webp)

<center>包装里面东西</center><br>

![image-20211127210326960](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171429468.webp)

<center>主体</center><br>

![image-20211127210605967](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171427060.webp)

![image-20211127210357010](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211127210357.png)

<center>四铜管加背夹</center><br>

![image-20211127210431749](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171430604.webp)

<center>还送一管5g的TF7(京东69人民币)</center>



## 拆机

![image-20211127210632447](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171430908.webp)

<center>背部螺丝都卸下</center><br>

![image-20211127210704273](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432980.webp)

<center>拆完然后小把手拉开</center><br>

![image-20211127210748157](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432956.webp)

<center>
  拉出来后，把开关排线断开，分离机箱和主板
</center><br>

![image-20211127210851572](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432558.webp)

<center>
  如果你接了sata盘先段断开，因为要把主板从这个托盘分离<br>
</center>

![image-20211127210946233](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432896.webp)

<center>卸下四个角的固定螺丝</center><br>

![image-20211127211050403](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432637.webp)

<center>分离主板和托盘，现在可以主板的背部</center><br>

![image-20211127211129829](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432875.webp)

<center>主板背面有一个隐藏的m2(只能11代的pcie4.0才可以使用)</center>



## 卸下旧风扇

![image-20211127211242656](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432432.webp)

<center>
  先断开风扇的电源
</center><br>

![image-20211127211352748](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432359.webp)

<center>
  扭动这个卡扣结构，让塑料柱从主板出来
</center><br>

![image-20211127211447414](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432971.webp)

<center>
  稍稍注意然后用力就可以拔起散热
</center><br>

![image-20211127211524639](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171432215.webp)

<center>
  旧散热(英特尔自带盒装散热)
</center><br>

![image-20211127211605510](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433878.webp)

<center>
  移除散热以后CPU的硅脂印记
</center>



## 装上新的AXP90

![image-20211127211754631](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433998.webp)

<center>
  解开膜(非常重要，这个膜不接会严重影响散热效果)
</center><br>

![image-20211127211841539](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433402.webp)

<center>
  送的TF7来个x涂抹硅脂(推荐x法点硅脂)
</center><br>

![image-20211127212028885](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433604.webp)

![image-20211127212112804](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433629.webp)

<center>
  然后把散热器本体放上去
</center><br>

![image-20211127212127581](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433281.webp)

<center>
  小心倒过来，然后把背板放上去
</center><br>

**注意注意注意！！！**

![image-20211127212210597](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433787.webp)

![image-20211127212337970](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433744.webp)

<center>
  这里的螺帽两种规格，我收到默认装载的是短的，但是这个短的不适用于deskmini-h470，会导致距离不够，然后压主板，切记切记一定要更换
</center><br>

![image-20211127212453081](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433533.webp)

<center>
  最后把风扇的电源接上
</center>



## 装后优化

![image-20211127212539374](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433995.webp)

![image-20211127212629336](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433134.webp)

<center>
  组装主板托架和主板的时候，红色位置会顶主板，可能会造成主板变弯(不是可能，是一定)，所以不要压的很紧，只要能固定不晃动就行了
</center><br>

![image-20211127212732895](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433264.webp)

<center>
  关于主板变弯我的解决办法是1.不要完全压死。2.把背板掰弯让主板的突出的螺丝有空间
</center><br>

![image-20211127212912555](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171433631.webp)

<center>
  最终样子还挺好看的
</center><br>

![image-20211127212944215](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434247.webp)

<center>
  接上开机电源的排线
</center>



## 1mm遇到的问题以及解决方法

![image-20211127213142498](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434843.webp)

![image-20211127213544052](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434708.webp)

<center>
放回去的时候就遇到的问题了,发现卡住了，搞不进去
</center><br>

![image-20211127213611188](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434586.webp)

<center>
  因为这里卡住了，所以我打算把这个螺丝拆了，然后把顶往外弹性掰一掰
</center><br>

![image-20211127213724207](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434886.webp)

<center>
  发现螺丝卸下来以后，这里出现了很多冗余
</center><br>

![image-20211127213830029](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434489.webp)

<center>顺势就直接塞进去了，然后我看了一下这个螺丝是扭不回去的，并且为了以后还要进行升级cpu或者其他部件，就没有必要强扭回去，因为现在的结构也相对固定，少了这两个螺丝也没啥区别。最后稳定性也非常好，这个网也不会卡风扇，整体非常满意</center><br>

![image-20211127214019244](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434875.webp)

<center>因为高度多了1mm，导致螺丝拧不上，风扇顶出来差不多一丢丢，不过不影响使用</center>



## 后言

![image-20211127215952591](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211127215952.png)

<center>左图是更换之前，右图是更换之后</center>

一图胜千言，该怎么做就不用我多说了。确实很厉害，为我压10900es打下了良好基础，给我鼓舞了信心，等用一段时间，有合适的机会就入一块10900es，体验一把10C20T的感觉。

对了，AXP有个缺点，就是太吵了，研究了一下发现AXP90最低的转速都是1600rpm，即便是30多度它也用1600rpm来跑。所以去bios里面设置一下转速，低任务下保证静音，高任务下保证性能释放

![image-20211127215158225](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434411.webp)

<center>刚开始设置成静音模式就好了，结果发现最低还是1600rpm的转速</center><br>

![IMG_5160](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang202307171434474.webp)

<center>
  必须要设置成自定义，图上是我的设置
</center>
