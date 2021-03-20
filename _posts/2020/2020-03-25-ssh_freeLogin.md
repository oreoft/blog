---
layout: post
title: 配置免密登陆服务器
excerpt: 搞懂操作和原理，举一反三
category: linux
keywords: linux, macos, other
---

## 前言

原来自己学习的时候在阿里云买自己的学习机，一台主机自己瞎折腾。但是参加工作以后管理的主机越来越多了，上服务器看的频率也越来越频繁，虽然有时候shell管理工具可以很方便的保存，但是mac的终端实在是太香了，使用命令联通万物，配合一些ssh_config和hosts设置可以轻而易举的上服务器，这不比xshell酷和方便吗😏

![2021-03-20 15.35.33](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320153638.gif)

免密登陆除了方便适用场景也非常多，公司代码一般都是配置ssh拉取，在github上配置了你电脑的公钥以后拉提起代码就不用输入密码也不用把密码记录到本地。

## 教程

### 了解ssh协议

ssh使用的是不对称加密的一个协议，后面我写https会详细介绍，简单来说两台主机使用非对称加密进行通信，通信和被通信的主机都需要拥有不同的秘钥，一般给发起通信方给出去的叫做公钥，自己留的叫做私钥，这个公钥和私钥都是进行解密数据的，为什么要整这么麻烦不直接http连接呢，周所周知http是透明协议，他的报文可以是没有加密的这不安全。利用 SSH 协议可以有效防止远程管理过程中的信息泄露问题。

![image-20210320155341605](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320155341.png)

### 生成公钥和私钥

这里是linux和mac的操作，win可以点击[这里](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh)，查看github官方教程

1. 打开终端，然后输入

   ```shell
   ssh-keygen -t rsa -C "www.someget.cn" -b 4096
   // 其中-t是后面是加密算法，默认rsa，我这里画蛇添足只是想告诉大家
   // -C是加入注释，一般都是自己的用户名
   // -b是指定秘钥长度
   // 以上参数都是无视，直接输入ssh-keygen也可以
   ```

![image-20210320155625787](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320155625.png)

<center>第二个高亮是指定私钥地址，这里直接回车选择默认路径就好</center>

2. 生成完了以后，在终端下面命令， 应该可以看到至少两个文件，一个是id_rsa还一个是id_rsa.pub，其中后缀为.pub的为公钥。把这个公钥发给你需要建立的通信方，对方就可以和你免密建立连接。

```shell
cd ~/.ssh & ll
// 去用户目录下面的.ssh查看下面的情况
```

### 把公钥给需要免密的主机

1. 问题来了，既然这个.pub是发起通信方创建的，凭啥你给我.pub你就可以和我建立连接（建立连接意味着可以建立控制关系），刚刚只解决可以解析报文，现在解决如何能同意对方连接。

2. 其实我刚刚里面有三个文件，还有一个authorized_keys的文件，这个文件里面记录了别人的公钥，也就是说只要别人的公钥在我这个authorized_keys里面，那么我就会可以解析对方的报文，并且同意对方连接。再提醒，这个authorized_keys是记录别人的公钥的，所以我们的公钥需要写到我们要免密登陆的主机上面。

3. 那我们刚刚已经生成的公钥，那我们现在写入到我们要免密登陆的主机上吧

   

   ![image-20210320161552356](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320161552.png)

<center>cat查看公钥信息，然后复制到剪贴板</center>

![image-20210320161840872](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320161840.png)

<center>我修改host, 然后进行ssh登陆，还没配置需要密码</center>

![image-20210320162038994](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320162039.png)

<center>登陆上主机，打开用户目录下面的.ssh文件</center>

4. 这里注意，这个公钥和私钥都是我之前生成过的，如果你没生成过它里面是没有的，这个authorized_keys是需要自己创建的，还有一个known_hosts这是连接过的信息，有人连接过这个主机，会自动生成这个文件并且在里面添加一条记录

```shell
mkdir authorized_keys
echo "你的刚刚复制内容" >> authorized_keys
// 这样你就完成了配置了
```

5. 最后你就可以直接登陆你的主机了

## 扩展

1. 讲道理，这个ssh的非对称加密只使用公钥和私钥来进行鉴权，如果对安全不敏感，你可以分发自己的私钥、公钥和authorized_keys文件，这样在很多集群直接就可以相互通信，而不需要每一台都生成key，然后再进行每一台互相写入公钥。大数据集群直接很多这么使用，但是这有悖非对称加密的初衷。

2. 如何配置github免密登陆

   - 点击https://github.com/settings/keys

   - ![image-20210320162844959](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320162844.png)

     <center>点击这个按钮</center>

   - ![image-20210320163001570](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320163001.png)

     <center>输入完在点击添加</center>

   - 然后你就可以使用ssh拉取代码啦



​           





