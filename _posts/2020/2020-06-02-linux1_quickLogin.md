---
layout: post
title: 快速连接上linux
excerpt: 比免密登陆再快一点
category: linux
keywords: linux, other, macos
---

## 前言

本文适用于喜欢原生终端的用户，钟爱第三方ssh客户端的可以无视....客户端可以保存用户信息和密码，比较无脑。mac可以使用终端，win可以使用git的bash。

上次分享了配置非对称秘钥免密登录，连接起来其实已经比较方便了, 但是还存在一个问题，假设我的用户名是hadoop，我的主机是192.168.99.6。那么我使用终端连接的命令为```ssh hadoop@192.168.99.6``` 

每次都要打这么一长串，挺麻烦的，至少简单来看，主机地址可以更改host文件来实现配置一个映射。用户名一般都是一个常用的账户，如果不加可以有一个默认的用户那就最好的。可喜的是这些都可以实现。最终可以达到```ssh myEcs```就可以连接上，如果需要其他账户登陆```ssh root@myEcs```也挺方便的。下面就给大家分享如何配置



## 配置hosts给主机'取别名'

ssh使用的是tcp协议进行通信，一般大家登陆服务器都是直接使用服务器公网ip的22端口。不太会给服务器登陆绑定一个域名。这就导致主机无规律会比较难记，只能够记在notes上或者使用第三方工具。我们可以在电脑上给服务器的ip配置一个单机域名，因为域名的解析会优先查找本地hosts文件，没有解析成功才回去访问dns服务器。所以在hosts文件里面增加一条记录可以达到给主机‘取别名‘的作用，各系统hosts文件路径如下

Win：```C:\Windows\System32\drivers\etc\HOSTS```

Mac&&Linux: ```/etc/hosts```

mac直接```sudo vim /etc/hosts```修改即可，具体操作和格式如下

![image-20210530104050034](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530104050.png)

<center>修改host</center>

修改成功后，可以ping一下，查看是否修改成功，电脑是否可以正常解析。例如上述文件中，有一些软件屏蔽的host，正常浏览器访问xmind.net应该是会进入xmind的官网，我们ping一下看一下

![image-20210530104444109](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530104444.png)

<center>可以看到已经被解析成本地的localhost了</center>



## 设置ssh的默认账户

使用ssh命令连接远程服务器，如果主机号前面不给任何的东西，默认的登陆用户是你目前登陆电脑的用户名

![image-20210530110743536](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530110743.png)

<center>我本地用户名是oreoft</center>

一般公司服务器或者生产环境的设备肯定名字不会是你自己电脑用户名，所以我们需要更改一下这个默认用户。接下来告诉大家怎么配置

- 切换到ssh服务的路径下面```cd /etc/ssh```，一般关于客户端(连接者)的配置都在ssh_config配置，关于服务的(被连接着)的配置都在sshd_config下(注意多了一个d)

![image-20210530111259276](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530111259.png)

- 养成好习惯，编辑文件之前先备份一下```sudo cp ssh_config backup```

![image-20210530111524973](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530111525.png)

- 然后进入编辑```sudo vim ssh_config ```，里面有很多已经写好的配置，我们换到最后开辟一个小空间，增加自己的配置

![image-20210530112027660](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210530112027.png)

按照上面配置一些就可以实现ssh convenient everywhere了



**全文END**

