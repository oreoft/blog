---
layout: post
title: 使用webhook进行方便的blog部署
excerpt: WebHook超方便的~~~~
category: linux
keywords: other, linux
---

## 前言

原来blog文章的更新都是写完然后提交到gitee的仓库，然后再登到机子上去git拉代码，有时候改动了config还需要重启一下jekyll的服务。为此我还特意写了一个shell脚本来做到，可以直接在本地shell里面ssh执行这个远程脚本

![image-20210714145903971](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714145904.png)

<center>原来配置的脚本</center>

最近了解到Webhook的概念，有点控制反转的味道，核心是前端不主动发送请求，完全由后端推送。由服务器发起请求然后再处理客户端的回调，现在Github和Gitee都支持WebHooks处理，然后我配置了一下发现实在是太好用了，基本上只要把代码提上去，blog就自动更新了，有时候随手写了一些笔记，因为很懒所以每次都成批发，所以真的是大爱这个功能。



## 配置

以Gitee的Webhook为例，其实Github也一样，先熟悉一下流程

你push代码到gitee->gitee收到pull然后去调用你服务器的接口->你服务器收到回调以后执行本地的发版操作。

下面我们来一步一步搞定，我们需要反着来，上面的执行流程，我们配置流程需要

1. 先编写发版流程脚本
2. 编写供Gitee回调的接口(放心有轮子)
3. 在gitee上配置webhook
4. push提交你的代码

#### 编写发版流程代码

这一部分，我是用的是jekyll，jekyll是支持热部署的，所以我只要把远程仓库上面的代码拉取下来，hekyll会自动监视文件变化然后实时渲染。但是因为我每次都可能会调整一些格式和配置，并且我的网站能够容忍稍微几秒钟无法对外服务，所以我每次都会重启一下服务，我就直接复用我上面的publish脚本

```shell
#!/bin/bash

echo -e "\033[31m ============== 正在暂停网站 ================= \033[0m"
pkill -f jekyll

echo -e "\033[31m ============== 正在清理缓存 ================= \033[0m"
jekyll clean

echo -e "\033[31m ============== 正在拉取最新文章 ================= \033[0m"
cd /root/blog && git pull

# 然后再重启进程
nohup jekyll server &
echo -e "\033[31m ============== 网站更新完成 ================= \033[0m"

# 使用github-webhookk必须使用exit退出
exit 0
```

#### 配置Gitee调用的接口

当然啦，你也可以自己使用python或者golang去启一个服务给Gitee去回调，然后回调的业务就是执行上述的脚本。

我这里使用一个[开源的项目](https://github.com/yezihack/github-webhook)， 也是使用golang写只需要启动服务的时候搭配上你的脚本地址，它的服务就可以提供给gitee调用，每次调用会执行你的脚本，用好开源工具真的能剩下很多事情呀。

安装步骤[README.md](https://github.com/yezihack/github-webhook#readme)已经很详细了，我这边就操作我的步骤，另外注意哈，这个开源项目的名字虽然叫github-webhook，但是本质上他就是在linux驱动一个服务而已，所以Gitee也是可以用的

1. 下载并且安装

```shell
// 执行
cd ~
wget https://github.com/yezihack/github-webhook/releases/download/v1.5.0/github-webhook1.5.0.linux-amd64.tar.gz
tar -zxvf github-webhook1.5.0.linux-amd64.tar.gz
cp ~/github-webhook /usr/local/sbin
chmod u+x /usr/local/sbin/github-webhook
```

![image-20210714165551764](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714165551.png)

2. 然后我们启动服务测试一下, 可以看到服务已经启动了，需要注意几个点
   1. 启动后他需要输入secret，这个是防止别人来刷你的接口，你可以设置一个自己的秘钥，到时候gitee那边也会让你输入这个，这样就只能让gitee来调用了
   2. 它开放的端口默认是2020，当然你可以启动的时候通过```--port```来指定，最关键的是你的防火墙和阿里云上面的安全组这个端口是必须开放的，不然gitee是无法回调成功的
   3. 可以看到gin打出来的路由，路径是```公网ip:端口/web-hook```, 其中ping是来给你测试的

![image-20210714170208330](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714170208.png)

<center>服务启动成功</center>

![image-20210714170647246](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714170647.png)

<center>可以看到ping成功啦</center>

3. 启动服务，那么刚刚是启动测试。现在我们完整的来配置一下

   1. 因为我的linux的防火墙已经关闭了，全权交给阿里来管理，我们需要在阿里云配置一下安全组，开放端口

   ![image-20210714171206820](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714171206.png)

<center>开放2020端口，我觉得挺好的，所以就没改</center>

  2. 使用```nohup github-webhook --bash ~/bin/publish --secret mysecret -q &``` 来进行后台启动，这里和java -jar是一样的.(注意--bash后面路径要换成自己的脚本)

     ![image-20210714171537391](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714171537.png)

     <center>secret已经打码处理</center>

     ![image-20210714171633135](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714171633.png)

<center>可以看到已经可以pingpong上了</center>

#### 然后我们在Gitee上配置

1. 直接去gitee里面你项目的管理界面，有一个webhooks，不想找我这里提供一个路径，但是你们可能需要替换一下```https://gitee.com/{你的用户名}/{你的项目名}/hooks```

   ![image-20210714172310475](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714172310.png)

2. 然后在这里输入你的url信息和秘钥就行啦(秘钥这边要选择签名秘钥，然后输入刚刚你自己启动服务时候键入的参数)，然后事件回调仅仅选择push就好，这样你提交代码他就会去执行代码

   ![image-20210714172417220](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714172417.png)

#### 提交你的代码

现在我把这篇文章的代码提交，看看会发生什么

1. 首先我同样配置了一个webhook的钉钉机器人，它给我提醒啦

![image-20210714173309303](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714173309.png)

2. 我们查看输出日志，发现是执行成功的，当然啦，你们看到这篇文章肯定是微博

   ![image-20210714190228913](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210714190228.png)

<center>查看输出日志</center>



## 后言

以后写好笔记可以直接提，然后会自动部署，太方便啦，爱啦，爱啦