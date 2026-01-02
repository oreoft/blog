---
category: linux
excerpt: Understand the operations and the underlying principles, and apply the same
  thinking to similar cases
keywords: linux, macos, other
lang: en
layout: post
title: Configure Passwordless Server Login
---

## Preface

Back when I was learning on my own, I bought a “practice machine” on Alibaba Cloud and just tinkered with a single server. But after I started working, the number of servers I manage kept growing, and I ended up logging into servers more and more often. Sure, some shell management tools can save sessions pretty conveniently, but the macOS Terminal is just too good. One command connects everything. With a bit of `ssh_config` and `hosts` setup, you can hop onto servers effortlessly—how is that not cooler and more convenient than Xshell 😏

![2021-03-20 15.35.33](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320153638.gif)

Passwordless login isn’t just convenient—it’s useful in tons of scenarios. Company code is usually pulled via SSH. Once you add your computer’s public key on GitHub, you can pull code without typing a password, and you don’t have to store the password locally either.

## Tutorial

### Understanding the SSH protocol

SSH uses an asymmetric encryption protocol. I’ll go into more detail when I write about HTTPS later. In simple terms: two hosts communicate using asymmetric encryption. Both the communicating host and the host being communicated with need different keys. Typically, the key you give to the party initiating communication is called the **public key**, and the one you keep to yourself is the **private key**. Both the public/private key pair are used for decrypting data.

Why make it so complicated—why not just connect over HTTP? As everyone knows, HTTP is a transparent protocol: its packets can be unencrypted, which is unsafe. Using the SSH protocol can effectively prevent information leakage during remote management.

![image-20210320155341605](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320155341.png)

### Generate a public key and private key

This is for Linux and macOS. For Windows, click [here](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh) to see GitHub’s official tutorial.

1. Open Terminal, then enter:

   ```shell
   ssh-keygen -t rsa -C "www.someget.cn" -b 4096
   // -t specifies the algorithm; default is rsa. I’m being extra here just to tell you.
   // -C adds a comment, usually your username
   // -b specifies the key length
   // You can ignore all of these and just run ssh-keygen
   ```

![image-20210320155625787](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320155625.png)

<center>The second highlight is the private key path—just press Enter to use the default path</center>

2. After it’s generated, run the following in Terminal. You should see at least two files: `id_rsa` and `id_rsa.pub`. The one ending with `.pub` is the public key. Send this public key to the party you want to establish communication with, and they’ll be able to set up a passwordless connection with you.

```shell
cd ~/.ssh & ll
// Go to the .ssh directory under your home directory and check what’s inside
```

### Give the public key to the host you want passwordless access to

1. Here’s the question: since this `.pub` is created by the party initiating communication, why should I accept your `.pub` and let you connect to me (connecting basically means you can establish a control relationship)? What we solved earlier was “being able to decrypt messages”; now we need to solve “how to approve the other side’s connection.”

2. Actually, I mentioned three files earlier—there’s also a file called `authorized_keys`. This file stores other people’s public keys. In other words, as long as someone’s public key is in my `authorized_keys`, I can decrypt their messages and I’ll approve their connection. Reminder: `authorized_keys` stores **other people’s** public keys, so our public key needs to be written onto the host we want to log into without a password.

3. So we’ve already generated the public key—now let’s write it to the host we want passwordless login on.

   

   ![image-20210320161552356](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320161552.png)

<center>Use cat to view the public key, then copy it to the clipboard</center>

![image-20210320161840872](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320161840.png)

<center>I modified the host and then SSH’d in—still needs a password because it’s not configured yet</center>

![image-20210320162038994](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320162039.png)

<center>Logged into the host and opened the .ssh folder under the user’s home directory</center>

4. Note: this public/private key pair was generated earlier by me. If you’ve never generated one before, it won’t exist. `authorized_keys` needs to be created manually. There’s also `known_hosts`, which contains connection history—once someone connects to this host, this file is automatically generated and a record is added.

```shell
mkdir authorized_keys
echo "你的刚刚复制内容" >> authorized_keys
// And that completes the configuration
```

5. Finally, you can log into your host directly.

## Extra

1. Honestly, SSH asymmetric encryption uses only the public/private key pair for authentication. If you’re not super sensitive about security, you can distribute your private key, public key, and `authorized_keys` file. That way, machines in a cluster can communicate with each other directly, without generating keys on every node and then writing public keys to each other one by one. A lot of big data clusters do this, but it goes against the original intention of asymmetric encryption.

2. How to set up passwordless login for GitHub

   - Go to https://github.com/settings/keys

   - ![image-20210320162844959](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320162844.png)

     <center>Click this button</center>

   - ![image-20210320163001570](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320163001.png)

     <center>After filling it in, click Add</center>

   - Then you can pull code via SSH