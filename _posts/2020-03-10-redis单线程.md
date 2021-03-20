---
layout: post
title:   
excerpt:  
category: 
keywords: 
---

1. 今天看到一个问题，说redis备份机制，那肯定是rdb和aof，rdb里面有一个bgsave，这个bgsave顾名思义在后台备份，可是大家说redis是单线程的啊，为什么还有能bgsava呢。
2. 首先redis，已经很多地方使用到多线程了，其次这个bgsava其实是fork出一个进程。然后讲解一下
3. 然后解释一下进程和线程之间的关系

