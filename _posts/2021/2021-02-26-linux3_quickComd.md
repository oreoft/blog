---
layout: post
title: Linux环境配置文件的一些应用
excerpt: Linux定制命令，简化指令提升效率
category: linux, others
keywords: linux, Mac, others
---

## 前言

上次介绍了startup文件的种类和作用，这一篇分享一下我是如何利用和特性完成一些我所需要的功能，也算是我自己的一些应用。注意本文都操作```~/.bash_profile```, macos从10.15开始已经更换成zsh，shell启动已经不再自动加载并执行bash的startup，请在```~/.zshrc```添加下文的指令或者在```~/.zshrc```添加```source ~/.bash_profile```。

老规矩，先说我的痛点然后给出我的解决方案，大家看看对自己是否有帮助再决定是否往下看。

我博客的代码托管在github上，运行在一台linux服务器上。每次我要更新内容```我需要把本地代码提交到云端，然后上服务器拉取代码，然后把线上服务停机，然后clean博客缓存，然后拉取代码，最后再启动服务```。每次都要这一堆步骤，作为一名程序员很自然的想到的使用脚本实现，这几个串行的指令非常简单。写完以后每次需要切到脚本目录下面然后./执行，有点懒，所以我希望能够可以把这个脚本变成```ps```一样anywhere可以执行的命令。

然后我还有一个场景，这个场景可能不需要写一个脚本，只是单纯一个命令特别长，背肯定是背不下来的，每次都需要复制粘贴，或者使用↑(如果期间敲了很多其他的命令就不好处理了，by the way 你当然可以使用history来查看，但是recode有上限)。例如，每次我启动spark-shell需要指定一大堆参数信息和依赖地址.....十几行这可不是正常人能背下来的，每次都复制粘贴吗？这可不太优雅。

这本来分享，我是如何来解决这两个场景下的烦恼的，分别是```添加PATH环境变量```和```给指令设置别名alias```

## 添加PATH环境变量

上次介绍过环境变量以及其中比较重要的PATH，再简单说一下就是你每次在终端输入命令，系统都会把PATH上面的目录都遍历一遍，看一下命令是否在里面，如果在则执行，如果没在则```command not found```。

所以如果我们想要把我们自己的写的脚本变成命令，需要做两个步骤，我们拿一个```echo “echo hello someget”```简单脚本来举例

1. 创建一个脚本---```echo "echo hello someget" > my_script```

![image-20210601200144757](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601200144.png)

<center>创建脚本文件</center>



2. 给这个脚本添加可执行的权限---```chmod a+x my_script``` 其中a表示所有用户，+表示赋予权限，x表示执行权限

   ![image-20210601200242619](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601200242.png)

<center>可以看到变成绿色了，并且有可执行权限</center>

3. 我们分别执行项目下的my_script和直接执行命令my_script试试

![image-20210601200342695](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601200342.png)

<center>可以看到执行权限设置成功，但是在非本目录下无法执行</center>

4. 把命令添加到PATH下，anywhere都可以使用，强烈建议在账号目录下mkdir一个bin的目录(名字随便，但是约定俗成bin下放可执行文件)，把这个bin文件配置在PATH下，然后以后自己写的脚本都可以放在这个bin下面。

   1. 创建bin，文件----```mkdir ~/bin```

   ![image-20210601201342022](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601201342.png)

   2. 把我们的my_script移到我们自己的bin文件夹中----```mv my_script ./bin```

   ![image-20210601203046457](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601203046.png)

   <center>移动到自己的bin文件夹</center>

   2. 修改PATH, 因为我linux是bash，所以建议在~/.bash_profle上把路径加到PATH上，如果你不清除我在说什么，可以看一下我原来写过的介绍[linux的startup篇](https://www.someget.cn/other,%20linux/2020/06/02/linux_evnFile)和[linux的环境变量篇-----](https://www.someget.cn/other,%20linux/2020/06/02/linux2_envVar)---```vim ~/.bash_profile```

   ![image-20210601202221960](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601202222.png)

   <center>使用冒号连接</center>

   3. 使用source刷新文件或者重新打开窗口我们再执行试试----```source ~/.bash_profile ```

   ![image-20210601203250790](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601203250.png)

   <center>不用在这个文件夹执行也可以啦</center>

   **最后**,  以后的脚本都可以放在这里bin下面，放进去以后就可以全局当成命令使用了。

   > 再次复习一下
   >
   > 1. export是更新环境变量的命令，使环境变量生效，关闭shell以后会失效，每次都需要export一下。所以把export写入startup文件每次shell启动的时候会执行一下
   > 2. PATH使用冒号进行拼接，如果你定义了两个PATH，记得把上一个使用```$```符号把原来定义的PATH也拼接到新的PATH上(因为你不确定其他文件是否还定义了PATH, 所以强烈建议直接在已有的PATH上使用```:```拼接，实在要再定一个PATH，请开头引用$PATH)

   

   ## 使用alias给你的命令取一个别名

   alias是linux的一个映射命令，它允许你映射已有命令。例如我们最常用的```ll```命令，其实就是对```ls -lh```的映射，不同的发行版处理不一样，例如在win下git提供的bash，就没有ll命令，如果你想统一操作习惯，你可以手动添加，稍后会给出方法。我们先验证一下我刚说的， 如果单纯在终端输入alias，会列出所有映射的记录，我们在使用管道过滤出含有```ll```的记录， 发现最后一天就是```ll='ls -lh'```

   ![image-20210602105544112](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602105544.png)

   <center>使用alias列出所有映射，并且筛选出含有 ll 的</center>

   ![image-20210602105936260](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602105936.png)

   <center>或者使用which，我们也可以查询到映射关系</center>

   既然有alias映射，那我们处理非常长的命令就非常好办了，依然我们用一个简单的命令来代替实际的需求。把hello 映射成``` 'echo hello someget' ```(这里注意和脚本的区别，第一个是脚本而这个是直接的命令)

   1. 因为alias非常简单，所以我们可以直接把执行命令```alias hello='echo hello someget'```

   ![image-20210602110455821](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602110455.png)

<center>可以看到已经正常使用了</center>

2. 但是alias和export一样，关闭了shell窗口就失效了，然后我们很自然的想到，可以写入到startup文件中

   1. ```vim ~/.bash_profile  ```
   2. 添加 ```alias hello='echo hello someget'``` （注意```=```左右两遍不能有空格）

   ![image-20210602112337811](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602112337.png)

   3. 重新开一个终端或者```source ~/.bash_profile```

至此再怎么开关shell，都可以使用hello输出hello someget了。使用这个方法，你同样可以配置```ll='ls -lh'```。或者任意你觉得很长的指令，例如一些常用的启动命令，每次手敲记不住，cv又觉得很烦。

## 后言

startup文件还有很多非常有用的作用，因为它shell启动就会自动执行的特性，可玩性很强。这是我分享的一些我自己的应用，如果你也有很有帮助的操作，我也希望你可以分享给我。
