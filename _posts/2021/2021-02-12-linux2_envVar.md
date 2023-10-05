---
layout: post
title: Mac和Linux环境变量那些事
excerpt: 常见环境变量文件总结
category: linux
keywords: linux, Mac, others
lang: zh
---

## 前言

本文对于概念性内容适用于各个操作系统，实操和命令内容仅适用于linux和mac(如果下文说linux下默认干嘛干嘛，mac也有这个操作)，欢迎大家尝试使用类Unix操作系统办公，走出舒适圈发现新的天地~😋

我很喜欢linux强大的一点，就是可以通过一个黑乎乎的小窗口可以完成各类操作，完成各类操作的难免会有一些环境变量的配置。以下是维基百科的定义

> An environment variable is a dynamic-named value that can affect the way running processes will behave on a computer.
>
> They are part of the environment in which a process runs. For example, a running process can query the value of the TEMP environment variable to discover a suitable location to store temporary files, or the HOME or USERPROFILE variable to find the directory structure owned by the user running the proces

我的理解就是简单把它当成变量来理解，我们编写的程序有变量，系统也有变量或者把它认为是常量，有固定系统常量，也有每台计算机都不一样的常量，需要手动配置的常量。比如在安装golang的sdk时，需要配置GOROOT并且还有同步修改到PATH上, 如维基百科所言环境变量相等于是系统运行时的动态变量，它对应用程序有影响。以GOROOT为例，这个变量代表的含义是go安装的路径，可能其他go的依赖库会使用这个变量，但是每台电脑安装的路径都不一样，所以需要大家都约定一个叫GOROOT的变量。我刚开始学习Java时，jdk正常，程序也能跑，一些依赖jre的组件会抛出找不到JAVAHOME的错误。

## 环境变量-PATH

最常见的环境变量是PATH，PATH可厉害了，在终端系统收到指令首先会去PATH所在的路径下来寻找有没有可以执行的指令或者文件，若找到则交给系统核心执行，如果没有找到则提示报错(win是Path，类Unix是PATH)。还是上面的例子，为什么要给java配环境变量，是因为我们想要java这个命令，刚刚把jdk下载下来然后解压路径是这样的

![image-20210530145438417](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530145438.png)

<center>jdk解压后目录</center>

![image-20210530145525491](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530145525.png)

<center>打开bin目录，我们常见的命令都在bin下面</center>

![image-20210530145649567](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530145649.png)

<center>使用本文件夹下的java命令，查看版本</center>

如果你没有把这个bin目录放在PATH上，你每次都只能通过路径找到这个命令，不能够直接输入java，否则会提示command not found，注意所有命令都是这样的，你可以通过which来查询，这个指令所在的路径，然后可以肯定这个路径一定在PATH上。

举个例子，我们查询一下我们常用的```ps```命令在哪里，然后使用把PATH打印出来(忘记提了，使用```$```符号可以手动引用变量，配合echo可以打印出来)

![image-20210530153322695](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530153322.png)

<center>可以看到ps所在的根目录的bin下，是在PATH变量中的</center>

## 配置

那么我们如何定义或者修改环境变量呢，我们可以通过执行```export -p```来获取当前shell所有可用的环境变量

![image-20210530154702303](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530154702.png)

<center>查看当前shell所有可使用的环境变量</center>

这里使用了export命令，它可新增，修改或删除环境变量，供后续执行的程序使用。

![image-20210530155343462](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530155343.png)

<center>定义一个num的环境变量</center>

在这个shell窗口里面，你可以任意的使用num(记得使用需要加```$```)， 但是你一定关闭了这个窗口这个环境变量就失效了。在Linux下提供多种环境配置文件可以在Linux启动或者创建shell窗口时就帮你执行一下这个export，这样你每次进来就可以使用这个环境变量了，是不是很聪明的亚子。

以最常见的bash举例，bash提供多种环境配置文件，在以.bash_profile为例，这是一个隐藏文件，它在用户目录文件下。每次shell启动会加载这个文件，在这里export环境变量每次都可以生效了。改完以后重开一个窗口就会生效，如果不想重开可以使用```source ~/.bash_profile ``` 重新加载。
