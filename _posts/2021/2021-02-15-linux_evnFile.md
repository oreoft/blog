---
layout: post
title: Linux的环境配置文件(startup文件)
excerpt: bash_profile和bashrc的区别
category: linux
keywords: linux, Mac, other
---

## 前言

环境配置文件其实这个名字是我瞎叫的，bash手册中把这类文件成为startup文件，可以想象成是一个脚本，每次启动的时候都会初始化一遍，当然这不是bash才独有的。这类startup文件并不单一，这导致了其实都可以实现需求，但是每次不知道更改哪个，你可能在网上能看到各种各样更新环境变量的教程，它们修改的startup可能都不相同，这样对萌新也会造成困扰。bash是目前Linux系统中最常用的shell，从 macOS Catalina 版开始macOS使用zsh作为默认的shell和交互式shell(当然你也可以敲一下bash切换回去)，并且macOS为了兼容bash用户的操作习惯，依然保留的bash的startup文件，但是shell启动并不会自动激活，需要手动配子一下(后面会说)



## shell模式

介绍区别之前，先介绍一下shell模式

- 交互式shell和非交互式shell

- 登录shell和非登录shell

首先，这是两个不同的维度来划分的，一个是是否交互式，另一个是是否登录。

所谓交互的意思就是在终端上操作shell会堵塞等待你传入，你按了回车以后它会执行你的命令。还有一种是非交互，shell不与你进行交互，而是读取存放在文件中的命令，并且执行它们。当它读到文件的结尾EOF，shell也就终止。

所谓的登陆就更好理解了，就是看你是否需要账号密码登陆shell，例如你在shell中输入bash， 界面会变成下面这个亚子，这就是非登录shell

![image-20210601171818735](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601171818.png)

<center>非登录shell</center>



## 常用startup文件

我们先罗列有哪些，注意这些都是可以环境配置文件，每次登陆都会被执行(注意其实还有logout文件，每次退出shell都会执行，但是用的比较少这里就不作介绍)

- bash下

/etc/profile

/etc/bashrc

~/.bash_profile

~/.bashrc

~/.profile

- zsh下

/etc/zprofile

/etc/zshrc

~/.zshrc

~/.zprofile

## 区别(两种常用shell)

看似很多，但是其实分一下类就比较好理解了

---

- 按照目录分

1. /etc下面的startup是系统初始化文件(注意/etc下都是非隐藏文件)，当打开一个shell没登录的时候都会执行，相当于每个账号都会执行

> The systemwide initialization file, executed for login shells。

2. ~/下面的startip是账号初始化文件(~/下都是隐藏文件)，仅当前登陆的账户执行

> The personal initialization file, executed for login shells。

**总结**

```tex
他们作用都是一样的，只是作用范围不一样，~下面的仅这个账号会生效，/etc下面所有账号都会生效，用于设置所有用户共同的配置。
```



- 按照后缀分类

1. 可以看到上面其实很有规律，一个是profile后缀，是一个rc后缀，他们的功能也非常类似，只是在shell的运行模式上有一些不同，bash运行有“登陆”和“交互式非登陆”两种属性。
2. “登陆shell”启动时会加载“profile”系列的startup文件
3. “交互式非登陆shell”启动时会加载“rc”系列的startup文件。

> When bash is invoked as an interactive login shell, or as a non-interactive shell with the –login option, it first reads and executes commands from the file /etc/profile, if that file exists. After reading that file, it looks for ~/.bash_profile, ~/.bash_login, and ~/.profile, in that order, and reads and executes commands from the first one that exists and is readable. The –noprofile option may be used when the shell is started to inhibit this behavior.
> When a login shell exits, bash reads and executes commands from the files ~/.bash_logout and /etc/bash.bash_logout, if the files exists.

**注意**

```tex
1. rc是run command的意思
2. bash下~/.profile有加载顺序，它是替补队员，只有读取并执行~/.bash_profile文件失败才会读取并执行~/.profile文件
```

- 按照shell分类

1. 名字已经很直白了，大部分就是shell名字后面加上profile或者rc，例如bash下有/etc/bashrc和~/.bashrc；zsh下有/etc/zshrc和~/.zshrc
2. zsh下profile，叫做zprofile

**注意**

```markdown
在10.15系统以后mac下也保留bash的配置文件(此时默认的shell是zsh)，如果需要生效需要在~/.zshrc</br>
加上```source~/.bash_profile```，这样相当于系统自动加载~/.zshrc的时候这个文件又去触发加载.bash_profile
```



## 后言

在不同的发行版中会有略微的不同，centos下大致如此，想要更加详细的探究，不放在相应的配置文件里面echo一些话来亲自测试验证。

最后对于众多不单一的startup文件，我的建议是如果你想对bash的功能进行设置或者是定义一些别名，推荐你修改~/.bashrc文件，这样无论你以何种方式打开shell，你的配置都会生效。而如果你要更改一些环境变量，推荐你修改~/.bash_profile文件。具体这类启动文件可以做什么[跳转点击](https://www.someget.cn/linux/2021/02/12/linux2_envVar.html)
