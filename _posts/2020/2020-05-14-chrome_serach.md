---
layout: post
title: Chrome的强大搜索功能
excerpt: Chrome的强大搜索功能
category: other
keywords: other，tools
lang: zh
---

## 前言

前几天一个好朋友求助我，大概问题是他的电脑QQ啥都能上网，就浏览器上不了网不是IE而是chrome，我第一反应可能是dns问题。后来发甩过来一张图，好家伙把我吓得，类似于下面这张图

![image-20210404201324306](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404201324.png)

<center>这图是我自己截的，大概意思是这样</center>

当然我朋友人也不笨硕士在读，新买电脑慕名装了chrome，这让我哭笑不得，当然我也看到过很多同事或者朋友，他们不用谷歌搜索，每次都会在输入框键入www.baidu.com然后等弹出网站来在进行检索内容。这个方法肯定是没有错的，只是觉得这样很慢，当然人家习惯啦，不愿意打破习惯，也没必要强迫。我这里分享一些我觉得很好用的chrome搜索设置，大家如果觉得好用可以自己摸索一下。

## 修改默认搜索引擎设置

### 什么是默认搜索引擎

其实chrome虽然是谷歌家的亲儿子，但是因为反垄断法，chrome还是能让你修改浏览器的默认搜索引擎的。当然这里的默认搜索引擎是指你在地址栏直接去搜索东西，而不用跳对应的网站搜索以及你在网页右键选中文字弹出来的快捷搜索选项

![image-20210404201930677](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404201930.png)

<center>地址栏回车搜索</center>

![image-20210404202028488](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404202028.png)

<center>右键选中文字弹出来的菜单</center>



### 如何修改默认搜索引擎

打开chrome浏览器，右上角三个点里面选择设置，然后在设置里面选择搜索引擎设置

![image-20210404202215013](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404202215.png)

<center>右上角三个点-设置-搜索引擎设置</center>



这里可以选择默认的搜索引擎

![image-20210404202610485](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404202610.png)

## 板凳搜索引擎

### 什么是板凳搜索引擎

板凳搜索引擎这个名字是我瞎取得，因为我不知道这个功能叫什么名字，我解释一下什么意思，就是他不是默认搜索引擎，但是你需要他的时候他又可以快速切换，一图胜千言

![2021-04-04 20.32.49](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404203330.gif)

<center>演示板凳搜索引擎</center>



### 原理

这个是怎么做到的呢，所有的检索网站的查询都是Get请求，请求路径都是固定的，变化的仅仅就你检索的关键字。

例如百度搜索1024，它的路径是https://www.baidu.com/s?wd=123

再例如百度搜索996，它的路径是https://www.baidu.com/s?wd=996

所以对于百度搜索来说，只要替换wd=后面的值就可以达到快速搜索的要求了，chrome给我们提供了很方便的切换板凳搜索的功能。

我这里列出我比较常用的网站的一些统配查询网站

```html
// 百度
https://www.baidu.com/s?wd=%s
// 京东
https://search.jd.com/Search?keyword=%s&enc=utf-8&wq=%s
// 淘宝
https://s.taobao.com/search?q=%s
// 网易云
https://music.163.com/#/search/m/?s=%s
// 微博
http://s.weibo.com/weibo/%s?frm=opensearch
// 值得买
https://search.smzdm.com/?c=home&s=%s
// 知乎
http://www.zhihu.com/search?q=%s
// B站
http://www.bilibili.com/search?keyword=%s
// maven中央仓库
http://mvnrepository.com/search?q=%s&ref=opensearch
// P站（当然我自己是不用的，特意给你做的）
https://www.pornhub.com/video/search?search=%s
```



### 设置

- 直接打开点击[这里](chrome://settings/searchEngines)或者点击下图的红框框

![image-20210404204144883](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404204144.png)

<center>点击红框框</center>



![image-20210404204240676](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404204240.png)

<center>这是设置界面列表</center>

- 图中可以看到已经设置好的搜索引擎，点击添加就可以添加你自定义的

![image-20210404204406996](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404204407.png)

<center>点击添加弹出来的页面</center>

- 这里有几个输入框，我分别解释一下，这个很重要决定了你如何搜索
  - `第一个输入框，这个就是一个名字而已，可以随便输，你只要你记得`
  - `第二个输入框，这个是你在地址栏激活板凳搜索引擎的关键字，输入你的关键字后按一下空格就进入了板凳搜索引擎。这里支持中文，字母小写，但是不支持字母大写`
  - `第三个是网站格式，我在上面已经把我常用的已经都列出来了，如果大家有自己的网站就自己随便搜搜索一个东西然后把你的关键字换成%s就好了`
- 点击添加后就就可以使用了，这个很宽泛，同一个网站你可以添加多个，例如我一般百度搜索我喜欢设置bd、baidu、百度都可以激活。按esc可以退回默认搜索引擎。

## 后言

其实挺简单的，但是很常用的功能，用惯了其实是回不去了了。我其实不排斥百度，我很多搜索引擎都用，我觉得百度一些本土化的东西做的好一些，准确率会高一些，因为都是他自家网站的东西，当然这不是夸它，只是无奈。其他搜索引擎我也用，反正我的目的就一个就是解决我的问题。

<center>分享一下我平时都是怎么搜索的吧</center>

![2021-04-04 20.51.39](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210404205349.gif)



