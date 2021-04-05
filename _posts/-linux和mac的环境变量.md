---
layout: post
title:   
excerpt:  
category: 
keywords: 
---

1. https://blog.csdn.net/duzilonglove/article/details/79729840
2. 如果你想对bash的功能进行设置或者是定义一些别名，推荐你修改~/.bashrc文件，这样无论你以何种方式打开shell，你的配置都会生效。而如果你要更改一些环境变量，推荐你修改~/.bash_profile文件，

准确的说，当shell是交互式登录shell时，读取.bash_profile文件，如在系统启动、远程登录或使用su -切换用户时；当shell是交互式登录和非登录shell时都会读取.bashrc文件，如：在图形界面中打开新终端或使用su切换用户时，均属于非登录shell的情况。

