---
layout: post
title:   
excerpt:  
category: 
keywords: 
---

## 前言

tcp每次发报文段然后回复ack效率其实很低，在确认应答策略中，对每一个发送的数据段，都要给一个ACK确认应答，收到ACK后再发送下一个数据段，这样做有一个比较大的缺点，就是性能比较差，尤其是数据往返的时间长的时候。使用滑动窗口可以一次性发送多个，窗口大小是发送端无需等待确认应答而可以继续发送数据的最大值，由接收端向发送端通知窗口大小。在传输数据过程中，可能会出现丢包，所以发送端需要设置缓存保留这些数据，直到收到他们的确认应答。收到确认应答后，将窗口滑动到确认应答的序列号位置，这就是滑动窗口控制。操作系统内核为了维护滑动窗口，需要开辟发送缓冲区，来记录当前还有那些数据没有应答，只有确认应答过的数据，才能从缓冲区删掉。接收端一旦发现自己的缓冲区快满了，就会将窗口大小设置成一个更小的值通知给发送端，发送端收到这个值后，就会减慢自己的发送速度。如果接收端发现自己的缓冲区满了，就会将窗口的大小设置为0，此时发送端将不再发送数据，但是需要定期发送一个窗口探测数据段，使接收端把窗口大小告诉发送端

当接收端收到自己应该接收的序列号以外的数据时，每个确认应答返回的是应该接收的序列号；当发送端连续收到3次相同序列号的确认应答，就会重发该序列号的数据。这种机制被称为高速重发机制，比超时重发更快速（快重传），所以发送端如何知道自己丢包了，定时器超时或者收到三个重复的ack

https://blog.csdn.net/dangzhangjing97/article/details/81008836



再看一下这个就可以写了

https://www.bilibili.com/video/BV1x4411d7HU?p=60

