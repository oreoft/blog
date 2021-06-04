---
layout: post
title: Charles服务端三大法宝
excerpt: repeat\mapping\compose
category: other，tools
keywords: other, macos，tools
---

## 前言

上次介绍了macOS下的抓包神器Charles的配置和简单的使用，今天我分享一下我平时是怎么使用它，除了最常见的监听请求查看报文信息的功能外。它还可以提升一些特殊场景下的效率(本文针对的是移动app项目分享，如果是普通web项目的话，可能chrome的F12更加方便一些)。比如公司项目一般肯定会有多个环境，比如生产环境、灰度环境、测试环境、本地环境等等。有时候测试环境出现问题，需要在本地环境找问题，如果静态浏览代码不易观察，通常会发送请求断点打进去。这个请求如果header和body参数特别多，每次发送请求都需要设置请求体非常麻烦，可能会有postman帮忙管理，可是众多的接口也是非常繁琐的。

幻想一下如果你使用手机在屏幕点击一下app响应的请求接口界面，请求可以直接访问本地起的服务器，直接把断点打到代码里面，这样是不是很方便的可以debug呢。今天就分享如何如何使用charles来重复发送请求和域名映射以及更改请求的host。

## 快速重复发送请求

有时候发送请求以后，在charles里面查看报文信息，服务重启以后需要看结果，看是结果是否达到自己预期。可以使用charles快速重复发送请求，因为反正你也要在charles看结果，这样会方便很多。

**可以选择一个请求右键选择repeat或者上面的顺时钟箭头**

![2021-06-03 14.52.54](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603145322.gif)

<center>快速重复请求</center>

## 使用域名映射重定向

这个是非常有用，你可以监听你设备的请求，把项目app的域名更改成localhost，然后你本地启服务，这样就可以达到app所有的接口请求都访问你电脑本地起的服务。方便查看日志或者debug。

这功能都可以在```charles菜单栏-tools-map remote```设置，下面有一个map local。这个不在今天的重点分享内，这个是把指定请求结构返回一个固定的结果(指定一个json文件，每次都返回这个结果)，可能mock数据有用，实际工作中我没有发现啥有用的地方，所以这里不做介绍。重点和大家说一下我是怎么使用map remote的

![image-20210603145854439](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603145854.png)

<center>域名重定向设置入口</center>

1. 介绍之前，因为隐私原因，不太方便拿自己家的产品来样式，我就祸害我经常背单词的一个软件，墨墨背单词(也算安利一下)来抓取并更改它的登陆请求

![image-20210603150819551](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603150819.png)

<center>正常返回401，鉴权错误，因为我账号密码随便打的</center>

2. 现在我本地已经齐了一个服务，接口也是```/api/v1/users/login```，但是返回结果有一点不一样。我们使用postman来测试

![image-20210603151154992](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603151155.png)

<center>这是我本地服务起得代码</center>



![image-20210603151028851](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603151028.png)

<center>这是我本地起的服务</center>



3. 那现在我就想使用墨墨背单词点击登陆，然后请求能够进入我的代码里面，并且message返回hello someget应该怎么办呢，两个办法。

   1. 第一个在charles的菜单栏选择tools-选择map remote-然后在界面选择add。在这里输入要映射的信息

   ![image-20210603151454689](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603151454.png)

   2. 第二个是选中一个请求记录，然后右键单击选择map remote

   ![image-20210603162937940](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603162937.png)

**两者的区别在于，后者会帮你自动填好监听的路径，不用自己填写了**

![image-20210603163733241](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603163733.png)

4. 那我们设置一下这个路径的映射，然后看一下请求能不能打到我们本地的服务

![image-20210603163846437](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603163846.png)

<center>设置好映射关系</center>

5. 可以看到我点击登陆以后，app一直处于等待响应堵塞状态，断点已经到idea了

![2021-06-03 16.41.27](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603164234.gif)

<center>断点已经成功进来了</center>

![image-20210603164356629](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603164356.png)

<center>客户端显示的是本地服务的报文信息</center>

6. 上面我们是设置了固定的接口映射，复杂情况下我们还可以把客户端所有的接口请求都重定向，设置规则这里有一个坑，需要提一嘴，比如要映射api.maimemo.com域名下面api开头的所有请求(现在微服务架构可能一个域名下面会绑定多个模块，每个模块用不同的api/来开头，其他服务模块正常走远程主机服务，只有指定模块想走本地服务)，那么远程主机路径后面使用```*```通配，本地服务留空，例如下面这样，值得注意的是远程要通配但是本地不需要。

![image-20210603171235558](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603171517.png)

<center>如果不需要区分/api，path留空则只做host重定向</center>

## 使用compose作为postman的增强

从主要功能上来说charles是看请求的，postman是发请求。但是.....charles也能发请求，在某种程度上会比postman会方便很多。使用charles可以复用很多由客户端已经发送的请求，这样你就不用再postman中再组织请求报文信息，甚至你可以把客户端请求保存转化以后导入到postman中。

最后一点点介绍一下，charles的compose功能。

1. 点击上面icon的一个小钢笔按钮，可以构建一个请求

![image-20210604112355103](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210604112355.png)

<center>构建一个请求</center>

![image-20210604112510742](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210604112510.png)

<center>输入url和请求方法</center>

2. 下图的1处可以添加一些请求参数，点击2的execute将发送这个请求

![image-20210604112623081](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210604112623.png)

3. 这发送显然不如postman来的方便，这compose最常用的是修改请求然后再发送。选中一个请求点击上面那个小钢笔或者右键这个请求然后选择compose。

![image-20210604112829240](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210604112829.png)

<center>右键选择compose</center>

4. 此时charles会把刚刚那个请求生成一条compose记录，你可以在这条记录的基础上对其进行修改，然后再execute发送，这样会方便很多，就不用再postman里面组织很多请求信息，方便调测。也可以直接修改host，复用客户端发送的报文信息直接给本地服务发送请求(我经常就这么做)。

![image-20210604113208581](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210604113208.png)

![image-20210604113241434](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210604113241.png)

## 后言

charles很强大，还有我觉得没有什么用，可是针对不同岗位的同学却非常有用的一些功能，这里我只能分享一些在我工作中用的非常多很提升效率的功能。当然肯定有很多我也不知道，但是潜在对我非常有用的功能等待我们去探索，我更期待你的分享~
