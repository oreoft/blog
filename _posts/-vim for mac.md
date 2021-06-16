---
layout: post
title: MacOS自定义快捷键一键休眠
excerpt: 找了很久终于找到优雅的方式了
category: other
keywords: other, macos
---

## 前言

Mac自带vim的默认配置文件在/usr/share/vim/vimrc。这个文件是系统级的vimrc配置文件，为了保证vim的正常运行，一般并不会修改这个文件。而是在～目录下创建一个新的用户级vimrc文件。在终端中执行
vi ~/.vimrc
随后在里面添加设置行号，语法高亮，tab退四格等基本设置。
set nu
syntax on
set tabstop=4
保存退出后就完成了。

