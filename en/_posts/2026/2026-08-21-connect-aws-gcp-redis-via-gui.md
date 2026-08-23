---
category: cloud
excerpt: 'Say Goodbye to Tedious and Fragile SSM Port Forwarding: Use SSH Tunnels
  to Give Desktop Clients Smooth Direct Access to Redis Across Multiple Environments'
keywords: aws, redis, elasticache, ssm, ssh-tunnel, gcp, memorystore, jumpbox
lang: en
layout: post
title: How to Elegantly Connect a Local GUI Client to a Private Redis on AWS / GCP
---

## Introduction

Recently, I was troubleshooting a Redis memory issue in production where usage was getting dangerously close to full. I wanted to dig into which keys were growing like crazy, whether there were any big keys, or data without a TTL set. In situations like this, the most intuitive approach is usually to fire up a local GUI tool—something like Another Redis Desktop Manager or RedisInsight—connect to Redis, and search or browse the data visually.

But if you’ve ever used managed Redis on AWS or GCP, you’ve probably run into the same wall: **cloud providers simply do not let you expose Redis to the public internet**.

Quick disclaimer first: in large companies with very strict compliance processes, connecting directly from your local machine to a production Redis instance might get you a lot of attention from the security team. But in many startups, small teams, or when you’re acting as the tech lead / ops person handling an urgent incident, being able to observe and diagnose production data quickly and intuitively is often far more practical than fighting through a pile of approval workflows.

So today I figured I’d write down why cloud providers absolutely refuse to give Redis a public endpoint, and how I moved away from the painful SSM command-line port forwarding workflow to a much cleaner setup using an SSH tunnel directly inside a GUI client.

## 1. Why can RDS be public, but Redis absolutely cannot?

When I first started using cloud services, this felt a little counterintuitive to me: on AWS or GCP, if you buy an RDS instance (PostgreSQL / MySQL) or Cloud SQL, you can usually just click a few buttons in the console, assign a Public IP, whitelist your own IP in the security group, and connect directly from your laptop.

But when it comes to ElastiCache or GCP Memorystore for Redis, the console doesn’t even offer a “public access” toggle. It’s hard-locked into a private subnet.

This really isn’t cloud providers being lazy. It’s mostly a consequence of Redis itself:

1. **Historical baggage and weak brute-force resistance**: Redis was originally designed with the assumption that it would run inside a **fully trusted internal network**. Early versions didn’t even have password authentication. Even though modern Redis supports Auth and ACLs, Redis can still handle hundreds of thousands of requests per second on a single instance, which makes password brute-forcing over the public internet extremely cheap for attackers.
2. **Dangerous commands and script escape risks**: Redis has a fairly broad privilege boundary. Commands like `CONFIG SET`, `EVAL` (Lua scripts), and module loading have all historically been involved in serious exploits where attackers used unauthorized access or weak passwords to escape the Lua sandbox, write files to the host machine, or even spawn a reverse shell.
3. **Its single-threaded model is easy to block**: Redis core request handling is single-threaded. If you expose it directly to the public internet, even a small amount of malicious traffic—or someone accidentally running an expensive `KEYS *`—can freeze the whole instance instantly and trigger a cascading failure across downstream services.

So cloud providers are very consistent on this point: **no matter how you configure it, Redis instances must stay inside the VPC private network**.

## 2. Why does AWS SSM port forwarding always feel awkward?

Since direct access isn’t possible, the traditional approach is to use an EC2 bastion host in the same VPC and rely on AWS SSM for local port forwarding:

```bash
aws ssm start-session \
  --target i-0123456789abcdef0 \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["my-redis-prod.xxxxxx.ng.0001.use1.cache.amazonaws.com"],"portNumber":["6379"],"localPortNumber":["6379"]}'
```

Once this command is running, your local `127.0.0.1:6379` is effectively mapped to the Redis instance in the cloud, and your GUI client can just connect to `localhost:6379`.

If you only need to run an occasional local test from code, this is actually pretty convenient. But if you frequently inspect data in a management tool, a few annoying pain points show up quickly:

- **Switching between environments is extremely tedious**: In real life you usually have `dev`, `stage`, and `prod`, and sometimes a dedicated Redis for recommendation systems or search. Every time you want to switch environments, you have to `Ctrl+C` the current session in the terminal, change the host parameter, and rerun the command. Or you end up opening a bunch of local ports like `6379`, `6380`, `6381`, and after a while you can’t even remember which port maps to which environment.
- **Idle sessions disconnect all the time**: SSM sessions have heartbeat and timeout behavior. If you step away from your computer for a bit without sending requests, or your laptop goes to sleep, the connection in the terminal quietly dies—often stuck at `Waiting for connections...`. Then you go back to the GUI tool, hit refresh, get a timeout, and have to restart everything from the terminal again.
- **You have to keep a terminal window open all the time**: Every day you end up wasting a terminal tab just to keep SSM running, constantly worried you’ll close it by accident.

## 3. A better approach: use a local key to connect through the bastion host directly

In fact, most modern Redis desktop clients—like Another Redis Desktop Manager and RedisInsight—already support **SSH Tunnel** natively.

![QQ_1787373870235](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260821234439597.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)
<center>(Image placeholder: the SSH Tunnel configuration screen in a desktop client; can be replaced during review)</center><br>

If you let the desktop client manage the SSH tunnel itself, save each Redis environment as a separate connection card, and just click whichever one you need, it can automatically bring up the tunnel and put it to sleep when idle. The experience becomes much smoother.

A lot of people get stuck here because **they can’t find the old PEM key for the bastion host, or their access has already expired**.

But if you already have permission to run AWS SSM commands locally, then you don’t need to ask anyone for a key again. You can simply generate a new public key on your own machine and use SSM to inject it into the bastion host in one shot.

### 1. Generate a dedicated SSH key pair locally
Run a single command in your local terminal to generate a standard RSA key pair (without a passphrase, so GUI tools can load it directly):

```bash
# Generate a key dedicated to the Redis tunnel
ssh-keygen -t rsa -b 2048 -m PEM -f ~/.ssh/my_redis_tunnel.pem -N "" -C "redis_tunnel_key"
```

### 2. Use AWS SSM to inject the public key into the bastion host
Find the EC2 instance ID of the bastion host in the same VPC that has a public IP, then send a CLI command that appends your public key to the bastion host’s `authorized_keys`:

```bash
PUB_KEY=$(cat ~/.ssh/my_redis_tunnel.pem.pub)

aws ssm send-command \
  --instance-ids "i-0123456789abcdef0" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[
    \"mkdir -p /home/ubuntu/.ssh\",
    \"chmod 700 /home/ubuntu/.ssh\",
    \"echo '$PUB_KEY' >> /home/ubuntu/.ssh/authorized_keys\",
    \"chmod 600 /home/ubuntu/.ssh/authorized_keys\",
    \"chown -R ubuntu:ubuntu /home/ubuntu/.ssh\"
  ]"
```

> **The idea is simple**: the AWS SSM Agent runs inside EC2 as a background daemon with `root` privileges. Once it receives instructions from the AWS API, it can write your public key directly into the allowlist, completely bypassing the classic deadlock of “you need to log into the server first in order to add your public key.”

### 3. Configure the connection in your Redis client

Now the bastion host already trusts your local private key, so open your Redis desktop client and create a new connection:

1. **General connection settings**:
   - **Host**: enter the Redis private endpoint (for example, `my-redis-prod.xxxxxx.ng.0001.use1.cache.amazonaws.com`)
   - **Port**: `6379`
   - **Auth**: leave blank if no password is configured
   - **TLS / Cluster**: choose based on your actual setup (for a standard primary-replica deployment, this is usually left unchecked)
2. **SSH Tunnel**:
   - **Check** ☑️ `SSH`
   - **Address**: enter the bastion host’s public IP (for example, `54.xxx.xxx.xxx`)
   - **Port**: `22`
   - **Username**: `ubuntu` (or the default username for your system image)
   - **Private Key**: browse and select the `~/.ssh/my_redis_tunnel.pem` you just generated
   - **Password / Passphrase**: leave blank

Click test connection, and it should work immediately.

## Summary

Once this is set up, the whole development experience improves a lot.

You can save `Prod-Redis`, `Stage-Redis`, and `Dev-Redis` as separate connection profiles in your GUI client. All of them can share the same bastion host and private key, while each one points to its own internal Redis host. From then on, whenever you need to inspect a specific environment, just double-click and connect. If the connection drops, the client can usually reconnect automatically, and you can finally stop keeping a pile of SSM terminal sessions running in the background.

In day-to-day development and operations, a lot of infrastructure security policies—like private network isolation—are non-negotiable. But by making good use of a bastion host and the native capabilities of your client tools, you can absolutely stay within the security boundary while still maximizing your local troubleshooting efficiency.