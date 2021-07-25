---
layout: post
title: Linux安装jekyll
excerpt: jekyll搭建博客yyds
category: other,tools,linux
keywords: other, tools, linux
---

## 前言

博客原来是搭建在github的pages上，后来因为确实github天气不好的时候访问速度堪忧，加上站点渐渐地有了一点流量，就想迁移阿里云的ECS了。正好趁着学生优惠买了一台1C2G1M的n4学生机，虽然丐版，但是当时应对我这小破站还是绰绰有余，后来有时候我自己访问有点卡了，因为上面没有计算型任务，考虑到可能是带宽瓶颈。后来想升级一下带宽，去阿里云看了一下，好家伙加1M就不能享受学生优惠了，升配要1k多，直接劝退。于是曲线处理把上面大多数静态资源都放在oss上面，平稳了一段时间。但近期感觉又不行了，但是加宽带太贵了，正好看到618的阿里云搞活动，n4机三年只要180元，而且再续费只要80元。就想买一台来做负载均衡结点，阿里云LBS普通的开发者一年才十几块钱，虽然带宽没有提升，但是可以分担一部分流量，应该会有一点作用，即便没有用这价格还有什么自行车啊，果断下手

![image-20210620171615038](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620171615.png)

<center>三年180，美滋滋</center>

买了以后初始化系统，需要重新安装jekyll，因为当时安装刚开始弄博客的时候因为jekyll走了不少弯路，当时也写了笔记，所以这次重新操作，就想记录下来，希望可以给也想使用jekyll组件博客的朋友一些帮助。网上其他文章，有些确实过期了，有些确实抄来抄去有点耽误人



## jekyll简介

> Jekyll 是一个简单的免费的Blog生成工具，类似WordPress。但是和WordPress又有很大的不同，原因是jekyll只是一个生成静态网页的工具，不需要数据库支持。但是可以配合第三方服务,例如discuz。最关键的是jekyll可以免费部署在Github上，而且可以绑定自己的域名。

上面是jekyll官方介绍，翻译成比较好懂的语言就是原来搭建博客需要有数据库，需要自己写js交互和css样式，但是jekyll可以不需要这些，它只需要你安装好jekyll然后选好一个主题，你写一篇markdown的文章，它就会帮你自动生成html并且还会启一个服务，按照markdown的名字变成url路径跳转。这也是目前比较流行的博客搭建方式，类似的框架还有Hexo。我之所以选择jekyll的原因是因为jekyll有一个我比较喜欢的主题......

[点击这里](http://jekyllcn.com/)，是jekyll的中文官网，中文官网有非常翔实的介绍，但是文中的安装方法可能不太适合国人环境。

## 安装jekyll

注意：本文非github的pages教程，是把jekyll安装到你自己买的linux服务器上，需要有自己的服务器

jekyll是使用ruby写的，所以我们需要安装ruby环境和gem的开发包。你可以去ruby官网下载sdk安装，但是我们一般会选择使用rvm来管理ruby版本，所以我们的步骤就是先装rvm，然后装gem，然后装jekyll

### 安装rvm

[查询秘钥](http://rvm.io/rvm/install)

```shell
# 1. 获取rvm的gpg密钥，这个秘钥可能会变，2021年6月20日正常
gpg --keyserver hkp://pool.sks-keyservers.net --recv-keys 409B6B1796C275462A1703113804BB82D39DC0E3 7D2BAF1CF37B13E2069D6956105BD0E739499BDB
```

![image-20210620191306849](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620191307.png)

<center>这一步失败，可能是网络原因，建议多长时间几遍</center>



```shell
# 2. 去rvm官网获取安装
curl -sSL https://get.rvm.io | sudo bash -s stable 
# 拉下来以后会自动安装，如果安装过程中提示秘钥错误，请查询最新秘钥
```

![image-20210620192047968](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620192048.png)

<center>看到图上内容就表示rvm安装成功</center>

```shell
# 刷新rvm的命令（使用source或者重新开一个窗口即可）
source /etc/profile.d/rvm.sh
```

![image-20210620192307389](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620192307.png)

<center>可以rvm -v 看看版本号检测是否成功</center>



## 安装ruby

```shell
# 查看ruby所有的版本
rvm list known
```

![image-20210620192529534](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620192529.png)

```shell
# 这里选择2.4版本，基于我的jekyll适配的主题定的，这个版本比较稳
# 如果不知道选什么，2.4肯定是最佳选择
rvm install 2.4
```

![image-20210620193240051](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620193240.png)

<center>等一会就下好了</center>



**接下来的步骤选做，如果你只使用ruby搭建博客，建议操作一下，可以把gem工具包的地址源切换成淘宝镜像，这样在国内速度会块很多**

```shell
# 删除默认的官方源
gem sources -r https://rubygems.org/
```

![image-20210620193316939](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620193317.png)

```shell
# 添加淘宝源
gem sources -a https://gems.ruby-china.com/
```

![image-20210620193346709](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620193346.png)



```shell
# 查看当前源
gem sources -l 
```

![image-20210620193358054](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620193358.png)



## 安装jekyll

```shell
# 使用gem安装jekyll
gem install jekyll
```

![image-20210620193640049](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620193640.png)

至此jekyll就安装完了，可以操作```jekyll init```命令生成一个空项目，然后简单的启动```jekyll s```查看(jekyll默认4000端口)

如果你已经有一个jekyll项目，可能你还需要做下列操作来更新自己的jekyll项目所以依赖的包，不然跑不起来

```shell
# 下载gem的包管理
gem install bundler:1.8
```

![image-20210620193659749](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210620193659.png)

```shell
# 切换到jekyll项目下，下载一下所需包和更新bundler包
gem install
bundler update
```

**END**

