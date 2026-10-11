---
category: other
excerpt: That Beelink mini PC at home had accumulated a whole pile of services on
  Windows. I tried Hyper-V, WSL2, and Docker on Windows one after another, but the
  stability just never got there. This time I decided to go all in and switch the
  host to PVE, then spin up separate VMs for Windows, Linux, Feiniu, and Hackintosh,
  allocating resources as needed.
keywords: pve, proxmox, windows, docker, hyper-v, wsl2, 黑苹果, 小主机, homelab, 折腾
lang: en
layout: post
title: Turning a Busy Little Windows Mini PC into a PVE Host
---

## Introduction

At home I have a Beelink SER mini PC with an R7 5800H CPU (8 cores, 16 threads), two 16GB DDR4-3200 sticks, and a 1TB NVMe SSD. My home broadband has a public IP, so it has basically been running 24/7 as a little home server.

It had been running Windows the whole time, but the more stuff I piled onto it, the less stable it became. This post is a record of why I eventually wiped it and reinstalled everything as PVE, how I did it, and how I split the machine up afterward. I also opened it up and cleaned out the dust along the way, so there are a few photos too.

p.s. This is more about the experience and the thought process, not a step-by-step tutorial.

## 1. More and more stuff ended up running on Windows

At first it was just a normal Windows PC, but over time I kept assigning it more and more jobs:

1. **Some services**: a few services I wrote myself (like an AI service), ddns-go (to automatically update my domain when my home public IP changes), an nginx gateway, and small proxy tools like hy2.
2. **NAS and smart home**: fnOS and HAOS (the Home Assistant OS).
3. **Windows-only apps**: a few apps only have Windows versions, so they can only run on Windows.

Out of all of these, only the third category truly depends on Windows. The first two were basically just being "carried along" by Windows.

## 2. Stability never really got there

Using Windows as the host had two main problems:

1. **Windows itself is resource-hungry**. The system drive easily grows to dozens of GB, there are a bunch of background services I never use, and it also eats up a big chunk of RAM.
2. **It restarts itself**. No matter how much I tweaked the update policy, every once in a while it would still find a chance to reboot. And once the host reboots, every service on top of it goes down together, including fnOS.

## 3. I changed the service setup three times

To make those services run more reliably, I went through three different setups.

### 1. The Hyper-V era

At first I ran services inside Linux VMs on Hyper-V (the virtualization platform built into Windows), and fnOS had always been running that way too. After using it for a while, I ran into three problems:

1. **Heavy resource usage**. Every VM has to run a full Linux system, so once you have a lot of services, each one carries its own OS overhead.
2. **Unreliable auto-start after power loss**. Sometimes after a power outage and recovery, the VMs would fail to come back up properly on their own.
3. **Too heavy overall**. Later I felt WSL was lighter, so I switched to WSL.

### 2. The WSL2 era

WSL2 is a Linux subsystem inside Windows, much lighter than spinning up full VMs, but then I ran into a new set of problems:

1. **Networking was annoying**. WSL supports mirrored networking (so WSL and Windows can share the same NIC and IP), but getting it set up was very fiddly.
2. **File transfers with the host were error-prone**. Service logs and various small files were stored on the Windows side, and WSL’s default file-sharing method would throw errors if both sides modified things at the same time. Later I switched to SMB sharing, which helped a bit.
3. **It would just exit on its own**. Even when services were clearly still running inside it, WSL would still quit by itself, so I had to write a keepalive script on the Windows side.

### 3. All In Docker based on Windows

So later I just installed Docker directly on Windows and put all services into containers. But Docker on Windows is still essentially backed by a WSL instance—it’s just a Docker-specific WSL, and what runs inside is still the Linux version of Docker. So that extra layer was still there, and so were the problems.

The most memorable example: forwarding UDP ports through Docker on Windows has to go through an extra layer, and sometimes you get this situation where **the container is clearly still alive, but the port is already unreachable**. To deal with that, I specifically set up a "companion" container for hy2: every 30 seconds it would do a real handshake, and if it failed, it would send an alert and automatically restart the service. It worked, but the fact that I needed a patch like that already said the foundation was wrong. On top of that there were all kinds of other random issues. Basically, it was just a pain.

After going through all three setups, the real problem was always at the host layer: as long as the host was Windows, its reboots, its resource usage, and its translation layer over the Linux ecosystem were impossible to avoid.

## 4. Why I switched to PVE

This machine is actually pretty capable, so there was no need to cram everything into one Windows install.

PVE (Proxmox VE) is a Debian-based virtualization platform. You install it directly on the physical machine as the host, and then manage VMs and containers from the web UI. After switching to it, the whole idea became:

1. **The host only does virtualization**, it doesn’t run business workloads itself, and it won’t randomly reboot.
2. **When I need Windows, I spin up a lightweight Windows VM** dedicated to those Windows-only apps.
3. **Everything else goes into a stable Linux VM**, where all Docker apps run natively, without any translation layer.
4. **Systems like fnOS and HAOS each get their own VM**.

That way I can allocate CPU cores and RAM to each system as needed, reboot only the one that has a problem, and keep them isolated from each other. Backups and snapshots are also built into PVE. It’s a much cleaner long-term setup, and adding more stuff later will be easier too.

## 5. Before getting started, I cleaned out the dust

Before doing anything else, I opened the machine up and cleaned out the dust.

![Two 16GB RAM sticks, and the 1TB SSD on the right](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003100309797.jpg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Two 16GB RAM sticks, and the 1TB SSD on the right</center><br>

Inside were the two 16GB RAM sticks, which I bought before memory prices went up, and next to them was the 1TB SK Hynix NVMe SSD. Overall, the hardware is still very solid.

When I took off the bottom cover, I had a moment of horror: **it turned out I had never peeled the protective film off the SSD thermal pad.**

![03-ssd-film](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095647224.JPG?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>The thermal pad on the bottom cover—the blue part is the protective film I never removed</center><br>

While cleaning, I also noticed there was a SATA connector on the bottom cover, which reminded me that I happened to have an old 2.5-inch mechanical hard drive lying around.

![An old HDD removed from an external enclosure](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003100159596.jpg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>An old HDD removed from an external enclosure</center><br>

This drive came out of a very old Apple computer, more than ten years ago. After I removed it, I barely used it and just kept it as a spare, even buying an enclosure for it back then to use it as an external drive. Now that I have an NVMe enclosure, it’s even less useful. So I figured I might as well put it into the mini PC and use it later as a spare or storage drive.

![Installing the HDD into the drive bay in the bottom cover](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095643186.jpg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Installing the HDD into the drive bay in the bottom cover</center><br>

The old drive is pretty thick. It’s still 2.5-inch, but it’s 9.5mm, so it didn’t really fit that well. After putting it in, the bottom cover bulged a bit. But once I tightened the four corner screws, it actually wasn’t sticking up too badly.

![The bottom cover bulges a little after installation](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095629924.jpg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>The bottom cover bulges a little after installation</center><br>

It ended up looking a bit like it had a round little "belly," which was kind of funny, but it didn’t affect usability. Later I formatted this drive and used it specifically for storing PVE VM backups.

## 6. Move the data out first

My Mac has 8TB of storage, which is more than enough for this migration data, so I moved everything there first. The amount of data that actually needed to be moved wasn’t that large:

1. **The fnOS virtual disk**: it used to be 250GB. I first copied the large files out separately, then reclaimed free space and compacted the virtual disk inside fnOS, and in the end it was only 33GB.
2. **Configs and data for the various services**: together they were only about 2GB. Docker images and code repositories could all be pulled again, so there was no need to carry them over.

After copying everything, I verified it all once before touching the machine.

![06-copy-fnos-files](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095548355.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>First copy the large files from fnOS to the Mac—more than 200GB</center><br>

![07-fnos-fstrim](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095544443.webp?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Ran `fstrim` inside fnOS and reclaimed 257GB of free space, which was the only way to compact the virtual disk</center><br>

## 7. Tweak the BIOS and install PVE

First I wrote the PVE image to a USB drive on my Mac.

![09-dd-iso](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095452415.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Used `dd` to write the PVE 9.2 image to a USB drive</center><br>

Then I went into the BIOS and changed a few things:

1. Enable virtualization: SVM (AMD CPU virtualization) and IOMMU (needed for device passthrough).
2. Power on automatically after AC loss: so I don’t have to physically press the power button after an outage.
3. Set the iGPU memory to 1GB (it used to be 3GB, because the Windows host might have needed it before; now I can lower it and free that memory up).
4. Set the system mode to performance mode and enable CPPC (so the system can adjust CPU frequency more finely; the frequency scaling driver on the PVE side depends on it).

![10-bios-main](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003094607877.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>BIOS home page, R7 5800H with 32GB RAM</center><br>

![11-bios-svm](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095355337.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Enable SVM</center><br>

![12-bios-iommu](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095457700.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Enable IOMMU</center><br>

![13-bios-ac-loss](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095348920.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Power on automatically after AC loss</center><br>

![15-bios-performance-mode](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003101926989.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Set system mode to Performance Mode</center><br>

![16-bios-cppc](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095421546.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Enable CPPC</center><br>

After that, I booted from the USB drive and installed PVE 9.

![17-pve-installer](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095312969.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>The PVE installer screen</center><br>

![18-pve-disk](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095011684.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Install the system on the 1TB SSD, using ext4 as the filesystem</center><br>

![19-pve-network](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095033142.jpeg?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Assign a fixed LAN IP to the host</center><br>

After installation, I did a bit of tuning: I set CPU scheduling straight to performance mode. This machine is plugged in and runs 24/7, so **I don’t care about power consumption, only performance**.

## 8. Splitting the machine up

Right now there are four VMs on PVE:

| VM | System | Specs | Purpose |
|---|---|---|---|
| ser-docker | Debian 13 | 4 cores / 4GB | All Docker services |
| ser-fnos | fnOS | 4 cores / 4GB | NAS, with the original virtual disk imported directly |
| ser-win | Windows Server 2025 | 4 cores / 6GB | Only runs Windows-only apps |
| ser-mac | macOS 15 (Hackintosh) | 8 cores / 8GB | For the Agent |

After moving Docker over, I immediately deleted that "companion" container I had made for hy2. On Linux, UDP ports are forwarded directly by the kernel, so the original problem simply doesn’t exist there.

This time I installed the Server edition of Windows instead of Windows 11. The Server edition has less flashy stuff, and system updates are easier to control, so it’s a better fit for running a few always-on applications. There was one small gotcha during installation: PVE gives the VM a VirtIO virtual disk, and the Windows installer doesn’t recognize it, so at first it couldn’t see any disk at all. I had to manually load the VirtIO driver first.

![20-winserver-no-disk](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095307993.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>The Windows Server installer can’t find the disk; you need to load the VirtIO driver first</center><br>

![22-winserver-autologon](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003095304834.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Use Sysinternals Autologon to enable automatic login at startup</center><br>

At the end I also set up a Hackintosh VM. I can’t pass the GPU through, and I couldn’t get graphics acceleration working either, so the UI is rendered entirely in software by the CPU, which does make it a bit laggy. But the CPU in this machine is still pretty decent, and if I’m not doing graphics-heavy tasks, it can brute-force most compilation work and web browsing just fine. **For the Agent, it’s absolutely enough.**

![QQ_1791036590133](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20261003090959062.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>Hackintosh running on PVE</center><br>

My daily-use Mac is already powerful enough, so the division of labor is simple: compilation, iOS development, and graphics-related work stay on my local Mac; miscellaneous tasks like web browsing get handed off to the Agent controlling that Hackintosh VM. The two don’t interfere with each other, and I don’t have to give up my own computer to the Agent.

## Closing thoughts

After years of tinkering, I tried Hyper-V, WSL2, and Docker on Windows, and in the end I realized the problem wasn’t the specific solution—it was the host. Once I switched the host to PVE, Windows went back to the role it’s actually good at: being a VM for Windows applications, while everything else returned to running natively on Linux.