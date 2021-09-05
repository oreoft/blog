---
layout: post
title: macOS下抓包神器-Charles
excerpt: charles简单介绍使用
category: tools
keywords: macos, tools, Charles
---



## 前言

> Charles 是一款HTTP代理服务器/HTTP监视器/反向代理服务器，当程序通过Charles的代理访问互联网时，Charles可以监控这个程序发送和接收的所有数据。它允许开发者查看所有连接互联网的HTTP通信，这些包括request, response和HTTP headers （包含cookies与caching信息）

以上是Charles官网的介绍，Charles总的来说就是一个http监视软件，它通过设置系统代理从而帮你转发http或者tcp(socket)请求，如果你有需求的话，这样你可以非常清晰的看到你所有的请求报文。在服务端的同学肯定会有强烈需求，这报文信息是和客户端同学交si流bi非常有效的凭证。不仅如此Charles还自带非常强大的功能，可以例如模拟弱网请求，设置断点更改报文然后发送，域名映射等等。本文分享Charles的简单使用。

p.s. 因为缺少win环境，所以操作环境是macos，win差不多相同，唯独资源需要自己找找

## 安装

1. 下载[这个连接](https://cloud.189.cn/t/YbQ7ZjqQZf63)，然后打开，一直点下一步，期间会让你输入密码，输入即可，这是一个脚本，需要权限写入应用文件夹

![image-20210602193631047](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602193631.png)

![image-20210602193853787](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602193853.png)

2. 激活步骤里面有秘钥，大家可以选择性激活体验，如果不用秘钥也可以使用只不过有应用启动等待15秒

![image-20210602194011616](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602194011.png)

<center>启动界面</center>

macOS下安装软件确实挺傻瓜的....没啥需要介绍的....

需要说明的是，Charles它可以监听你这台设备下的所有请求，也可以代理设置区域网下其他设备的请求(最常见的是抓取移动设备的app)，下面分别介绍如何配置

## 当前设备配置代理(装Charles的电脑)

![image-20210602194135014](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602194135.png)

<center>主界面</center>

1. 确认开启macos的代理，也可以在设置-网络-高级-代理-网页代理(http)代理

![image-20210602194905887](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602194905.png)

<center>charles设置打开代理</center>

![image-20210602195242917](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602195242.png)

<center>设置里面小勾勾钩上了，表示已经被charles接管了，charles默认端口是8888</center>

​	**如果想要修改端口可以在charles菜单栏proxy-proxy settings进行设置**

![image-20210603104054676](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603104054.png)

<center>修改端口</center>



2. 这个时候你已经可以进行简单的http的请求解析了，但是如果需要抓取https的话，还需要为你的电脑安装证书，这个证书可以使得浏览器信任charles。```help-ssl prcxying-Install Charles Root Certificate```。(ssl是https的使用的加密协议)

![image-20210602195454346](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602195454.png)

3. 找到这个证书，然后把这里所有东西都始终信任， cmd+s保存关闭的时候会提示输入密码，输入密码就好了

![image-20210602195905944](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602195905.png)

![image-20210602200016150](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602200016.png)

<center>最终会变成的亚子</center>

4. 设置ssl代理范围，Charles菜单栏选择proxy-SSL Proxying Setting

![image-20210602200249738](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602200249.png)

5. 首先勾选启动代理，然后添加需要代理的host，把host设置成通配```*```，然后端口443(https端口)

![image-20210602200412952](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602200412.png)

届时所有的http和https请求你都可以监听并且正常解析了， 我们测试一下

![image-20210602201006090](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602201006.png)

<center>知乎搜索123</center>

![image-20210602201231177](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602201231.png)

<center>获取界面</center>

## 界面介绍

![image-20210602203742464](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602203742.png)

<center>整体各个按钮的功能</center>

![image-20210602204004477](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602204004.png)

<center>界面布局</center>

![image-20210602204240060](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602204240.png)

<center>切换成时间顺序查看(和Fiddler一样)</center>

这个界面整体来说比较通俗移动，随便点一点就知道大概功能

## 抓取局域网设备(已移动设备安卓系统为例)

首先的大前提，就是要抓取的设备在同一个区域网这样才可以成功代理上，如果不在一个区域网那怎么办？答案是想办法弄到一个区域网上去，开热点，usb共享网络，内网穿透之类的，这个是大前提，否则下面的不用看了。

1. 抓取局域网设备核心步骤依然是设备设置系统代理，然后安装charles证书，唯独有区别的是，当前装charles设备代理的端口是localhost(127.0.0.1)的8888端口.而区域网其他设备它自己有自己的localhost，它不能设置成localhost，而需要设置成装charles这台设备的区域网ip。

![image-20210603102445303](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603102445.png)

<center>多种方式可以获取本机(装charles设备)ip</center>

2. 打开移动设备-设置-wlan-长按ssid-选择修改-代理选择手动-代理服务器输入装了charles电脑的ip，端口8888，其他的不用设置直接点保存

![image-20210603103653828](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603103653.png)

3. 此时charles会弹出远程代理，是否监听这个远程主机，点击allow。如果你不小心点了拒绝或者后面想要管理，你可以去charles菜单栏proxy-access conrtol settings里面进行管理。

![image-20210603103850991](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603103851.png)

4. 此时其实你已经可以抓取移动设备上浏览的简单的http请求，但是https快速推进的时代，很少有单纯的http网站，你没安装https证书极有可能一个网站都访问不了，并且频繁提示不信任证书，所以我们依然要像上面一样安装一下证书。安装证书有两种方式，第一种是想在电脑一样安装把证书下载下来然后传到手机，第二种就方便一些，访问一个charles搭建的内网网站即可下载，我们选择第二种
5. 在手机上访问```chls.pro/ssl```，然后点击安装输入一下密码就好了

![image-20210603104435864](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603104435.png)

<center>在这里可以看到安装的步骤</center>

![image-20210603104800450](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603104800.png)

<center>下载</center>

![image-20210603104821127](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603104821.png)

<center>下好了点一下就安装</center>

4. 最后手机访问知乎，在charles就可以看到知乎的https的报文信息啦(配置完如果没有请求，建议重启一下charles)

![image-20210603105014304](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603105014.png)

## 后言

简单的配置和基本的功能界面介绍就是这样，文章已经很长了，所以个别功能就没有很详细的做介绍，一方面是界面很通俗易懂说明大概功能大家点几下就可以get到，有空会分享一些我常用的功能来解决我工作上的一些痛点。
