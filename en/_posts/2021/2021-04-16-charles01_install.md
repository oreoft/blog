---
category: tools
excerpt: 'Charles: A Quick Intro to Using It'
keywords: macos, tools, Charles
lang: en
layout: post
title: 'A Must-Have Packet Sniffing Tool on macOS: Charles'
---

## Preface

> Charles is an HTTP proxy / HTTP monitor / reverse proxy server. When a program accesses the Internet through Charles’ proxy, Charles can monitor all the data that the program sends and receives. It allows developers to view all HTTP communications that connect to the Internet, including requests, responses, and HTTP headers (including cookies and caching information).

The above is the intro from Charles’ official website. Overall, Charles is an HTTP monitoring tool. By setting a system proxy, it helps you forward HTTP or TCP (socket) requests. If you need it, you can see all your request packets super clearly. Server-side folks will definitely have a strong need for this—packet details are a very effective “evidence” when communicating with client-side folks. Not only that, Charles also comes with a bunch of powerful features, like simulating a poor network, setting breakpoints to modify packets and resend them, domain mapping, etc. This post shares a simple walkthrough of using Charles.

p.s. Since I don’t have a Windows environment, the setup here is on macOS. Windows is pretty much the same—only the resources you’ll need to find yourself.

## Installation

1. Download [this link](https://cloud.189.cn/t/YbQ7ZjqQZf63), then open it and keep clicking Next. During the process it’ll ask for your password—just enter it. This is a script and needs permission to write into the Applications folder.

![image-20210602193631047](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602193631.png)

![image-20210602193853787](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602193853.png)

2. In the activation steps there’s a license key. You can choose to activate for the full experience. If you don’t use a key, you can still use it, but you’ll have to wait 15 seconds on app startup.

![image-20210602194011616](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602194011.png)

<center>Launch screen</center>

Installing apps on macOS is really pretty foolproof.... not much to explain....

One thing worth mentioning: Charles can listen to all requests from this device, and it can also proxy requests from other devices on the LAN (the most common case is capturing traffic from mobile apps). Below I’ll introduce how to configure both.

## Configure proxy for the current device (the computer with Charles installed)

![image-20210602194135014](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602194135.png)

<center>Main screen</center>

1. Make sure the macOS proxy is enabled. You can also find it in Settings - Network - Advanced - Proxies - Web Proxy (HTTP) Proxy.

![image-20210602194905887](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602194905.png)

<center>Enable proxy in Charles</center>

![image-20210602195242917](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602195242.png)

<center>The little checkbox is checked in Settings, meaning it’s been taken over by Charles. Charles’ default port is 8888.</center>

​	**If you want to change the port, you can set it via Charles menu bar Proxy - Proxy Settings.**

![image-20210603104054676](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603104054.png)

<center>Change port</center>



2. At this point you can already do basic HTTP request parsing. But if you want to capture HTTPS, you still need to install a certificate on your computer. This certificate allows the browser to trust Charles. ```help-ssl prcxying-Install Charles Root Certificate```. (SSL is the encryption protocol used by HTTPS.)

![image-20210602195454346](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602195454.png)

3. Find this certificate, then set everything here to Always Trust. Press cmd+s to save. When you close it, it’ll prompt you for your password—just enter it.

![image-20210602195905944](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602195905.png)

![image-20210602200016150](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602200016.png)

<center>This is what it’ll look like in the end</center>

4. Set the SSL proxying scope: in the Charles menu bar choose Proxy - SSL Proxying Settings.

![image-20210602200249738](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602200249.png)

5. First check Enable SSL Proxying, then add the host(s) you want to proxy. Set Host to the wildcard ```*```, and Port to 443 (the HTTPS port).

![image-20210602200412952](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602200412.png)

At this point, you can listen to and properly parse all HTTP and HTTPS requests. Let’s test it.

![image-20210602201006090](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602201006.png)

<center>Zhihu search 123</center>

![image-20210602201231177](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602201231.png)

<center>Captured view</center>

## UI overview

![image-20210602203742464](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602203742.png)

<center>What each button does</center>

![image-20210602204004477](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602204004.png)

<center>Layout</center>

![image-20210602204240060](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602204240.png)

<center>Switch to chronological view (same as Fiddler)</center>

Overall the UI is pretty straightforward—click around a bit and you’ll get the idea.

## Capture traffic from LAN devices (Android as an example)

The big prerequisite is: the device you want to capture must be on the same LAN, otherwise the proxy won’t work. If it’s not on the same LAN, what then? The answer is: find a way to get onto the same LAN—mobile hotspot, USB tethering, intranet tunneling, etc. This is the prerequisite; otherwise you can stop reading here.

1. The core steps for capturing a LAN device are still: set the device’s system proxy, then install the Charles certificate. The only difference is: on the machine with Charles installed, the proxy host is localhost (127.0.0.1) on port 8888. But other devices on the LAN have their own localhost, so they can’t set it to localhost. They need to set it to the LAN IP of the machine running Charles.

![image-20210603102445303](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603102445.png)

<center>Multiple ways to get the local machine’s (Charles host) IP</center>

2. On the mobile device: Settings - WLAN - long press SSID - Modify - set Proxy to Manual - set Proxy server to the IP of the computer with Charles installed, Port 8888. No need to set anything else—just Save.

![image-20210603103653828](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603103653.png)

3. Charles will pop up asking whether to allow remote proxying / listen to this remote host—click Allow. If you accidentally clicked Deny or want to manage it later, go to Charles menu bar Proxy - Access Control Settings to manage it.

![image-20210603103850991](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603103851.png)

4. At this point you can already capture simple HTTP requests from the mobile device’s browsing. But in today’s HTTPS-everywhere era, there are very few pure HTTP sites. If you haven’t installed the HTTPS certificate, chances are you won’t even be able to open sites, and you’ll get frequent “untrusted certificate” prompts. So we still need to install the certificate like we did above. There are two ways: the first is like on the computer—download the certificate and transfer it to the phone. The second is more convenient: visit a Charles-hosted intranet site to download it. We’ll use the second.
5. On the phone, visit ```chls.pro/ssl```, then tap Install and enter a password.

![image-20210603104435864](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603104435.png)

<center>You can see the installation steps here</center>

![image-20210603104800450](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603104800.png)

<center>Download</center>

![image-20210603104821127](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603104821.png)

<center>After it’s downloaded, tap it to install</center>

4. Finally, open Zhihu on the phone, and you’ll be able to see Zhihu’s HTTPS packet details in Charles (if you don’t see any requests after configuring, I recommend restarting Charles).

![image-20210603105014304](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210603105014.png)

## Afterword

That’s it for the basic configuration and a quick intro to the main UI and features. The post is already pretty long, so I didn’t go into every feature in detail. On one hand, the UI is easy enough that you can click around a few times and get it. When I have time, I’ll share some of the features I use most often to solve a few pain points in my day-to-day work.