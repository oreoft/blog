---
layout: post
title: 爷青结，idea的postfix功能
excerpt: 找了很久终于找到优雅的方式了
category: tools
keywords: other
lang: zh
---

## 前言

前面写了一篇idea的live templates动态模板功能介绍，说实话这个网上可参考的资料太多了，都是抄来抄去格式都不带换了，如果换了格式那就是它自己把格式cv的时候弄丢了。我原来一直有一个需求，就是想实现var.sout然后回车变成System.out.println(var);  我研究过好几次，我原来思路不对，我一直以为这是动态模板的功能，但是其实动态模板实现不了把这个var放到println()里面，并且var会在前面，然后我总觉得肯定是一些内置方法我没有掌握，还特意去翻idea的官方文档，把所有变量的内置方法都看了一遍又一遍，把idea自带的sout实现也研究好久，每次都放弃了。

举一个很简单的例子吧, 我想自己想用动态模板写一个.test实现sout功能

1. 第一步去设置动态模板

![image-20210404183921703](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404183921.png)

<center>设置一个test,并且应用到java-other</center>

2. 然后看效果

   ![2021-04-04 18.38.10](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404183959.gif)

<center>效果很蠢</center>

最后我在idea的文档中发现了有一个叫postfix Completion功能，我去idea一搜。把我吓一跳，原来我心心念念.var/.sout的实现，在这里！！！

![image-20210404184658588](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404184658.png)

<center>里面有大部分常用实现</center>

经过一段时间的琢磨，我想来进行总结一下，介绍idea自带的一些我比较常用，然后自己自定义的一些分享。

## idea自带postfix分享

- 快速生成for循环-num.fori

  ![2021-04-04 19.00.47](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191403.gif)

- 快速判空和判断非空-num.null&num.nn

![2021-04-04 19.15.09](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191701.gif)

- 字符串format拼接-string.format

![2021-04-04 19.16.20](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191918.gif)

- 快速new和快速生成引用-class.new&object.var

![2021-04-04 19.17.40](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191929.gif)

- 快速包裹异常代码-statement.try

![2021-04-04 19.18.32](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191935.gif)

- 快速返回-result.return

![2021-04-04 19.19.03](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404191941.gif)



大家应该可以看到这个和动态模板非常像，这也是我原来为什么一直找错方向的原因，这相当于动态模板plus，注意到这个我大部分时间都输入前几个次然后使用联想，这样巧起来非常舒服，产生bug效率upup😜

## 自定义postfix

### 解释

上面都是idea自带的一些postfix，我们自己也可以写。与动态模板差不多，但是这里没有group的概念，自定义的都会被写到java这里面。虽然说强迫症有点接受不了，但是这么提高效率，也就忍了。

那怎么写呢，最好的方式就是参考idea自带postfix是怎么实现的，我随便拿我原来心心念念的sout来解释

![image-20210404192600733](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404192600.png)

上图是sout的实现，我按照图上的标注，解释一下分别什么意思

1. 这是key值，就是.key，出发你这个postfix的条件
2. 这是适用于jdk版本，有些lambda语法可能只支持jdk8，可以在这里设置
3. 这里是应用于类型，一般这个写不写都好，写了可以更加健壮
4. $EXPR$表示expr.key。这个expr最后要放在那里
5. $END$是最后你的光标停在哪里

----

### 分享

首先，我只分享我的一些思路，我不把我的配置分享出来，不是我小气。而是我吭哧吭哧写半天，写完大家也有点creativity

- 写过scala的都知道toInt,toLong之类的直接转型有多香，而java只有toString，而且我经常因为NPE还不敢乱用，但是Hutool里面有一个静态类Convert，随便看一个toStr方法

![image-20210404193838992](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404193839.png)

<center>Convert.toStr()方法介绍</center>

![2021-04-04 19.41.40](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404194439.gif)

<center>我常用的转换演示</center>



- 集合判空，mybatis如果没查到数据ORM返回的对象是null，集合是一个空集合。如果你对集合判null大概率会不符合你的预期。虽然集合都有isEmpty()的方法很快判断里面是否含有元素，但是为了健壮这个习惯可不好，万一啥时候这个集合对象是null，压根就没有这个方法又NPE...下面是我的postfix方案

  ![2021-04-04 19.52.08](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404195552.gif)

<center>演示</center>



## 后言

其实这个有很多可以做，我真的是找了好久，果然还是多翻翻手册每次都会有新收获。我现在其实每天都在把idea的手册当成英语读物，原因一它里面很多单词都是cs专业词汇多背背以后肯定能用到；二其实我们对idea的挖掘我自己觉得还是比较少的，idea很强大不仅仅是国人瞎吹，还有很多可能少数人知道可以提高效率的方法等我们去探索。

附上idea文档，[点击](https://www.jetbrains.com/help/idea/2021.1/product-educational-tools.html)