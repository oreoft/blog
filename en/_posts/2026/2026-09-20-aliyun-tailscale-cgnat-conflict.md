---
category: cloud
excerpt: 'I wanted to repurpose an idle Alibaba Cloud machine into a service monitoring
  box. But after installing Tailscale, DNS, apt mirrors, and container registries
  all started failing one after another. The reason turned out to be that Alibaba
  Cloud places its internal services in `100.64.0.0/10`, which is the same range Tailscale
  uses. One of Tailscale’s anti-spoofing rules ended up dropping all of their return
  traffic.


  I’m writing this down to document the troubleshooting process, and the official
  Tailscale solution I ended up using.'
keywords: tailscale, aliyun, alibaba cloud, ecs, cgnat, iptables, rp_filter, systemd-resolved,
  dns, 网段冲突
lang: en
layout: post
title: Installing Tailscale on Alibaba Cloud Blocked All of Alibaba Cloud’s Own Internal
  Services
---

## Introduction

I’ve had an Alibaba Cloud machine sitting around for a long time. I bought it during a promo, and later renewed it for 20 years. The specs and bandwidth aren’t great (2 vCPU, 2 GB RAM, 3 Mbps), and since I usually manage more machines on GCP and use GCP more often, this one has mostly been idle.

Recently I wanted to give it something useful to do. I have a few servers at home running various services, and they go down from time to time—sometimes because the machine rebooted, sometimes because memory blew up. When a service dies, I usually don’t notice until something in production starts breaking. I’ve never had a unified monitoring setup. Using the home machines to monitor themselves doesn’t feel very reliable if they’re the ones going down; this Alibaba Cloud box may be underpowered, but it’s stable, which makes it a good fit for health checks.

My plan was to connect everything with Tailscale. Tailscale is a WireGuard-based networking tool that pulls machines scattered across different places into the same virtual private network. Each machine gets a `100.x.x.x` address, and they can talk to each other like they’re on the same LAN. I’ve installed it plenty of times on AWS and GCP machines and basically never had issues. But this time on Alibaba Cloud, right after installing it, DNS resolution, `apt` package installs, and pulling images from registries all started failing one after another.

The reason can be summed up in one sentence: **Alibaba Cloud puts its internal services in the `100.64.0.0/10` range, and Tailscale uses that same range.** On Linux, Tailscale installs an anti-spoofing firewall rule that drops any packet that "claims to come from that range but didn’t arrive through the Tailscale interface." Replies from Alibaba Cloud’s internal services got caught by that rule.

This post is a record of how I traced it down step by step, a few workarounds I tried along the way, and the official Tailscale solution I ended up using.

p.s. The system is Ubuntu 22.04, and Tailscale is 1.102.

## 1. What this machine is supposed to do

First, here’s how I planned to use it, because a lot of the decisions later are tied to this.

1. **Network access**: connect all services that need monitoring to the Tailscale private network. This machine will hit each service’s health check endpoint over the private network, then expose a dashboard.
2. **Access management**: normally I’ll manage it directly over the Tailscale network; on the public internet, I’ll only expose SSH on port 22, so I can still get in when I’m not on the private network.
3. **Dashboard access**: access the dashboard directly from inside the private network; when I’m outside it, use `ssh -L` to forward the dashboard port locally.



![Overall architecture](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260920223654647.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>Overall architecture: health checks and management go through the Tailscale private network, and only port 22 is exposed publicly</center><br>

Health checks, management, and dashboard access all go through Tailscale. So whether Tailscale can work properly on this machine is the prerequisite for the whole setup.

## 2. After installing Tailscale, DNS resolution completely broke

After installing Tailscale and joining the private network, domain resolution on this machine stopped working. `getent hosts` returned nothing:

```shell
$ getent hosts github.com
$
```

My first suspicion was upstream DNS or outbound connectivity. If that were the case, querying a public DNS server directly should also fail. So I checked:

```shell
$ dig +short github.com @8.8.8.8
20.205.243.166
$ dig +short github.com
;; communications error to 127.0.0.53#53: timed out
```

Querying `8.8.8.8` worked, but using the default resolver timed out. Outbound networking was fine, so **the problem was in the local resolution path**.

Ubuntu 22.04 uses `systemd-resolved` for local DNS by default: `/etc/resolv.conf` points to `127.0.0.53`, which is a local forwarding stub, while the real upstream resolvers are configured elsewhere. So I checked which upstreams it was using:

```shell
$ resolvectl status
Link 2 (eth0)
    DNS Servers: 100.100.2.136 100.100.2.138
Link 3 (tailscale0)
    DNS Servers: 100.100.100.100
```

The two addresses on `eth0` are Alibaba Cloud internal DNS servers provided by DHCP. The `100.100.100.100` on `tailscale0` is Tailscale’s own DNS, used to resolve machine names inside the tailnet. Tailscale calls this MagicDNS.

The address `100.100.2.136` is the important one here. Tailscale assigns machine addresses from `100.64.0.0/10`, which is the RFC 6598 reserved range for carrier-grade NAT (CGNAT), covering `100.64.0.0` through `100.127.255.255`. Alibaba Cloud’s internal DNS also falls inside that range.

If Tailscale applies restrictions to that range, Alibaba Cloud DNS would get caught too. So I looked at the iptables rules Tailscale had installed:

```shell
$ iptables -S ts-input
-A ts-input -i tailscale0 -j ACCEPT
-A ts-input -p udp -m udp --dport 41641 -j ACCEPT
-A ts-input -s 100.64.0.0/10 ! -i tailscale0 -j DROP
```

The last line means: **drop any packet whose source address is in `100.64.0.0/10` unless it came in through `tailscale0`.**

The intent of this rule is anti-spoofing. Every machine in the Tailscale network uses an address from this range, and legitimate Tailscale traffic should only arrive through the virtual `tailscale0` interface. If a packet comes in from a physical NIC but claims to be from `100.x`, that looks like someone pretending to be a Tailscale machine, so dropping it makes sense.

But Alibaba Cloud’s internal DNS also lives in that range. The machine sends a query to `100.100.2.136`, which goes out through `eth0` just fine; the reply comes back with source address `100.100.2.136`, enters through `eth0`, and gets hit by that rule.

![Rule matching: before the fix](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260920223706392.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>How the same rule treats three kinds of packets: spoofed packets and Alibaba Cloud replies look identical to it</center><br>

I verified it directly:

```shell
$ dig +short +tries=1 github.com @100.100.2.136
;; communications error to 100.100.2.136#53: timed out
$ dig +short +tries=1 github.com @223.5.5.5
20.205.243.166
```

Alibaba Cloud internal DNS timed out, while Alibaba Cloud’s public DNS `223.5.5.5` (outside that range) worked. That matched the theory.

One extra note: this rule has nothing to do with Tailscale’s exit node feature (using one machine as the internet gateway for other devices). As long as `tailscaled` is running, it installs this rule.

Actually, before reinstalling the OS, when I was doing some initial checks on this machine, I had already noticed that I couldn’t reach Alibaba Cloud’s instance metadata service at `100.100.100.200` (used for things like instance ID and security group info). It was blocked by the same rule. Back then it only affected metadata. This time it was DNS, which made the impact global—anything that needed domain resolution stopped working.

That also explains why I’d never seen this on AWS or GCP: their metadata service and DNS live in the `169.254.x.x` link-local range, not in the CGNAT range, so they never collide with this rule.

## 3. First workaround: switch DNS to public DNS

Once I knew the cause, there were a few possible directions:

| Approach | Problem |
|---|---|
| Add an allow rule in the `ts-input` chain | `ts-input` is managed by `tailscaled` itself and gets rebuilt on every start, so manually added rules get wiped |
| `tailscale up --accept-dns=false` | Prevents Tailscale from taking over DNS, but then I lose the ability to access other machines in the tailnet by hostname |
| Switch DNS to public resolvers outside this range | Works, but means no longer using Alibaba Cloud internal DNS |

At the time, I chose the third option. Alibaba Cloud’s DNS is provided via DHCP, so replacing it required changing two things together: first tell netplan not to accept DNS from DHCP, then explicitly set upstream resolvers for `systemd-resolved`.

```yaml
# /etc/netplan/99-dns-override.yaml
network:
  version: 2
  ethernets:
    eth0:
      match:
        macaddress: 00:16:3e:xx:xx:xx
      set-name: eth0
      dhcp4-overrides:
        use-dns: false
```

```ini
# /etc/systemd/resolved.conf.d/99-public-dns.conf
[Resolve]
DNS=223.5.5.5 119.29.29.29
```

Resolution came back, and MagicDNS was unaffected because it goes through the `tailscale0` interface.

## 4. The same problem showed up again with `apt`

After fixing DNS, I went to install Docker, and then `apt update` failed too:

```
W: Failed to fetch http://mirrors.cloud.aliyuncs.com/ubuntu/dists/jammy-security/InRelease
   Unable to connect to mirrors.cloud.aliyuncs.com:http:
```

On Alibaba Cloud Ubuntu images, the default package source is `mirrors.cloud.aliyuncs.com`, which is an internal Alibaba Cloud mirror. I checked what it resolved to:

```shell
$ getent hosts mirrors.cloud.aliyuncs.com
100.100.2.148   mirrors.cloud.aliyuncs.com
```

Still `100.100.x.x`, so it was the same root cause again.

Following the same logic as DNS, I switched the source to the public mirror `mirrors.aliyun.com`. This time it worked, but it was slow:

| | Time |
|---|---|
| `apt update` | 366 seconds |
| Install Docker | still not finished after 25 minutes |

The reason was bandwidth. **Traffic over Alibaba Cloud’s internal network is free and not rate-limited; public internet traffic has to squeeze through this machine’s 3 Mbps bandwidth.** A full Ubuntu `apt update` downloads over 100 MB of index files, which takes several minutes at 3 Mbps. Previously, using the internal mirror didn’t consume public bandwidth at all. Once that internal path was blocked, all traffic got pushed onto the public network.

At this point, I had hit the same root cause for the third time: metadata, DNS, and `apt` mirrors. Alibaba Cloud’s internal services mostly live in `100.100.x.x`. Replacing them one by one with public endpoints was just whack-a-mole, and every replacement consumed more public bandwidth. I needed to make the whole range work again.

## 5. Put an allow rule at the very top of the INPUT chain

As mentioned above, I couldn’t add a rule directly to `ts-input`, because that chain gets rebuilt. But iptables matches in order, and the `INPUT` chain only jumps to `ts-input` on its first line. If I allow Alibaba Cloud packets in `INPUT` *before* that jump, they’ll never reach the DROP rule:

```shell
iptables -I INPUT 1 -i eth0 -s 100.100.0.0/16 -j ACCEPT
```

The `-i eth0` restriction is the key: Tailscale’s own traffic comes through `tailscale0`, so this rule won’t accidentally allow spoofed Tailscale traffic.

After adding it, internal DNS, `apt` mirrors, and the metadata service all started working again.

Before making it persistent, I needed to confirm one thing: when `tailscaled` restarts, does it reinsert its own jump back at the top? If it does, my rule would get pushed down to line 2 and become useless. So I tested:

```
# Before restart
1    ACCEPT     all  --  100.100.0.0/16
2    ts-input   all  --  0.0.0.0/0

# After systemctl restart tailscaled
1    ts-input   all  --  0.0.0.0/0
2    ACCEPT     all  --  100.100.0.0/16
```

**It does.** Every time `tailscaled` starts, it uses `-I` to put its jump back at line 1, and my manual rule immediately stops being effective.

So it wasn’t enough to just save an iptables rule and restore it at boot. I needed to move the rule back to line 1 every time `tailscaled` started. I wrote a systemd unit that follows `tailscaled`:

```ini
[Unit]
After=tailscaled.service
PartOf=tailscaled.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/aliyun-internal-allow.sh

[Install]
WantedBy=tailscaled.service
```

`PartOf` makes it restart when `tailscaled` restarts, and `WantedBy` makes it get pulled in when `tailscaled` starts.

There was also a timing issue in the script: when the `tailscaled` service becomes active, its iptables rules may not have been installed yet. So the script first waits for the `ts-input` jump to appear, then moves my rule back to line 1:

```sh
for i in $(seq 1 30); do
  iptables -C INPUT -j ts-input 2>/dev/null && break
  sleep 1
done
iptables -D INPUT -i eth0 -s 100.100.0.0/16 -j ACCEPT 2>/dev/null
iptables -I INPUT 1 -i eth0 -s 100.100.0.0/16 -j ACCEPT
```

After restarting `tailscaled` again, the rule stayed at line 1. Then I switched both `apt` and DNS back to Alibaba Cloud internal endpoints:

| | Public mirror | Internal mirror |
|---|---|---|
| `apt update` | 366 seconds | 18 seconds |
| Install Docker | not finished after 25 minutes | 19 seconds |

## 6. The internal address for the image registry wasn’t in that range

After Docker was installed, I needed to pull images. Accessing Docker Hub from mainland China is basically unreliable, so I planned to use Alibaba Cloud Container Registry (ACR) as a relay. I checked the ACR internal endpoint:

```shell
$ getent hosts registry-vpc.cn-hangzhou.aliyuncs.com
100.103.7.180   registry-vpc.cn-hangzhou.aliyuncs.com
```

`100.103.x.x`—not inside the `100.100.0.0/16` range I had just allowed, so it would still be blocked.

Alibaba Cloud internal services are not all in `100.100.x.x`. To cover everything, I’d have to widen the allow rule to the full `100.64.0.0/10` range. Before doing that, I went to see how other people were handling this problem.

## 7. Community workarounds, and Tailscale’s official solution

There’s an issue on Tailscale’s GitHub describing this exact problem: after installing Tailscale on Alibaba Cloud ECS, internal DNS and `apt` both stop working. It’s still open. There are also quite a few Chinese blog posts about it. Summarizing the approaches I found:

| Approach | Notes |
|---|---|
| Move DNS and mirrors to public endpoints | Works, but consumes public bandwidth and requires changing services one by one |
| `--accept-dns=false` | Only fixes DNS; `apt` and image registries still fail |
| Manually insert allow rules | This is what I did above; you also have to deal with reordering when `tailscaled` restarts |
| `--netfilter-mode=nodivert` | Tailscale creates rule chains but does not attach the jump; you manage the jump yourself |
| `disable-linux-cgnat-drop-rule` | A node attribute provided officially by Tailscale |

Tailscale’s docs mention that `nodivert` was the recommended approach before `disable-linux-cgnat-drop-rule` existed, but now the latter is the recommended one.

`disable-linux-cgnat-drop-rule` is a node attribute. If you assign it to a specific machine in the Tailscale policy file, `tailscaled` changes that DROP rule in `ts-input` to RETURN: instead of dropping the packet, it hands it off to the following rules. Since this rule is generated by `tailscaled` itself, there’s no issue with it being overwritten on restart, which means I no longer needed that systemd unit babysitting my custom rule.

## 8. If anti-spoofing is disabled, what replaces it?

The official docs also mention the tradeoff: removing that rule removes the anti-spoofing protection, so machines on the local network could send packets pretending to come from Tailscale addresses. The recommended compensation is to enable reverse path filtering (`rp_filter`).

`rp_filter` is a kernel check: when a packet arrives, the kernel asks, "if I were to send a reply to this source address, which interface would I use?" If that doesn’t match the interface the packet actually came in on, the packet gets dropped. In strict mode (`rp_filter=1`), it has to be the exact same interface.

There was one thing I needed to confirm first: if Tailscale had installed a route for the entire `100.64.0.0/10` range via `tailscale0`, then replies from Alibaba Cloud DNS would also be considered "supposed to come in through `tailscale0`", and strict mode would drop them too, bringing me right back to square one.

So I checked Tailscale’s routing table. It uses table 52:

```shell
$ ip route show table 52
100.101.102.103 dev tailscale0
100.101.102.104 dev tailscale0
100.100.100.100 dev tailscale0
```

These are per-host routes, not a route for the whole range. Then I checked the return path for a few addresses:

```shell
$ ip route get 100.100.2.136      # Alibaba Cloud DNS
100.100.2.136 via 172.16.x.x dev eth0
$ ip route get 100.103.7.180      # ACR internal
100.103.7.180 via 172.16.x.x dev eth0
$ ip route get 100.101.102.103    # A machine in Tailscale
100.101.102.103 dev tailscale0
```

Alibaba Cloud internal services route back through `eth0`, and they also arrive through `eth0`, so they pass. If someone on `eth0` spoofs a packet pretending to be a Tailscale machine, the return path should go through `tailscale0`, which doesn’t match, so it gets dropped.

**Strict mode turns out to be exactly the anti-spoofing protection I needed, and it’s more precise than the old blanket DROP rule: it only protects real Tailscale addresses and doesn’t accidentally hit Alibaba Cloud.**

![Rule matching: after the fix](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20260920223718431.png?x-oss-process=image/auto-orient,1/resize,w_1200,limit_0/format,webp/quality,Q_80)

<center>After changing DROP to RETURN and enabling rp_filter, how the same three kinds of packets are handled</center><br>

## 9. What I actually changed

### 1. Add a tag and a node attribute in the policy file

```json
"tagOwners": {
  "tag:aliyun": ["autogroup:admin"],
},
"nodeAttrs": [
  {
    "target": ["tag:aliyun"],
    "attr":   ["disable-linux-cgnat-drop-rule"],
  },
],
```

I used a tag instead of applying it directly to my own account because this attribute affects all Linux machines, and I also have some Linux machines outside Alibaba Cloud joining the tailnet. There’s no reason to disable anti-spoofing on those. Using a tag lets me target only the Alibaba Cloud machines.

Before changing it, I backed up the original policy file. After editing it, I first called Tailscale’s validation API to make sure it was fine, and only then applied it for real.


### 2. Tag this machine with `tag:aliyun`

You can do this from the machine list in the admin console, or via the API. As soon as I applied the tag, the rule on the machine changed immediately:

```
-A ts-input -s 100.64.0.0/10 ! -i tailscale0 -j DROP
-A ts-input -s 100.64.0.0/10 ! -i tailscale0 -j RETURN
```

### 3. Enable `rp_filter`

```ini
# /etc/sysctl.d/999-ali-hz-tuning.conf
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
```

**The filename needs to start with `999-`—this is a weird Alibaba Cloud-specific pitfall**, which I’ll explain in the next section.

### 4. Remove the old systemd unit

The previous workaround was no longer needed. After removing it, the `INPUT` chain only had the `ts-input` jump left.

### Verification

```
Internal DNS   100.100.2.136     OK
apt mirror     100.100.2.148     HTTP 200
Metadata       100.100.100.200   OK
ACR internal   100.103.7.180     HTTP 401      ← previously it timed out
```

The 401 from ACR is expected—an image registry returns 401 if you haven’t logged in. The important part is that it responded; before, it just timed out. Docker container networking, SSH over the Tailscale network, and public SSH all worked normally too. I restarted `tailscaled` one more time, and the RETURN rule was still there.

## 10. Alibaba Cloud’s built-in sysctl config can override yours

Files under `/etc/sysctl.d/` are loaded in filename order, and **later-loaded files override earlier ones**. Alibaba Cloud images ship with a `99-apsara-sysctl.conf` file that contains these lines:

```ini
vm.swappiness = 0
net.ipv4.conf.all.rp_filter = 0
net.ipv4.conf.*.rp_filter = 0
```

It disables `rp_filter` entirely. If your config file is named something like `99-xxx.conf`, it may sort before `99-apsara`, and then get overridden back to 0 at boot.

I actually discovered this pitfall through `swappiness` first. In an earlier tuning pass, I had written `vm.swappiness = 10` in `99-ali-hz-tuning.conf`. If I loaded just that file with `sysctl -p`, the runtime value was indeed 10. But when I used `sysctl --system` to simulate the full boot-time load order, the result was 0—overridden by `99-apsara`. So every reboot silently undid it.

Renaming the file to start with `999-` fixed it, because it sorts after all `99-*` files (`9` has ASCII code `0x39`, which is greater than `-` at `0x2d`).

There’s another detail here: if you just use `ls`, `999-` may appear before `99-apsara`, because UTF-8 collation can ignore punctuation. But `systemd-sysctl`, which loads sysctl settings at boot, uses byte order. To see the real order, use `LC_ALL=C ls`:

```shell
$ LC_ALL=C ls /etc/sysctl.d/
...
99-apsara-sysctl.conf
99-sysctl.conf
99-tailscale.conf
999-ali-hz-tuning.conf
```

**To verify sysctl config, use `sysctl --system` and check the final value. Don’t rely only on `sysctl -p` for a single file.** The latter only tells you your file is syntactically fine; it doesn’t tell you whether it wins in the end.

## 11. Retrospective

**1. If you install Tailscale on Alibaba Cloud, do these steps first**

- In the policy file, give Alibaba Cloud machines a tag and add `disable-linux-cgnat-drop-rule`
- Enable `rp_filter=1`, and make the config filename start with `999-`
- Keep Alibaba Cloud’s default internal DNS and `apt` mirror config; no need to change them

If you do this before installation, you won’t run into the whole chain of problems above.

**2. If the same root cause shows up a second time, it’s time to look for the real cause**

This time I hit the same issue four times in a row: metadata, DNS, `apt`, and the image registry. DNS and `apt` were each "fixed" by switching to public endpoints, and each fix worked in isolation—but together they were just whack-a-mole, and every change consumed more public bandwidth.

**3. If you manually insert firewall rules, check whether some other program will rewrite them**

The rule I manually inserted into `INPUT` got pushed down to line 2 after `tailscaled` restarted. If I hadn’t verified that, the rule would have silently stopped working after some future restart.

**4. Check the official docs first**

Most community solutions involve writing your own script to insert rules, or using `nodivert`, but Tailscale already has an official node attribute for exactly this case. If I had gone through the docs earlier, I could have skipped that whole detour in the middle.

## Summary

The root cause this time was simple: Alibaba Cloud puts internal services in `100.64.0.0/10`, and Tailscale uses the same range. Tailscale’s anti-spoofing rule dropped all replies from Alibaba Cloud internal services. AWS and GCP put their internal services in `169.254.x.x`, which is why I’d never hit this before.

In the end, I used Tailscale’s official `disable-linux-cgnat-drop-rule`, combined with `rp_filter=1` to restore anti-spoofing protection. DNS, `apt`, and the image registry all went back to using Alibaba Cloud’s internal network, with no public bandwidth cost and no custom firewall rules to maintain. Along the way I tried public DNS, public mirrors, and manually inserted rules—each one worked at the time, but each only solved the immediate symptom for one service. The actual problem was a subnet conflict, and the final fix was also applied at the subnet level.

## References

- [CGNAT interoperability · Tailscale Docs](https://tailscale.com/docs/reference/cgnat-interoperability)
- [Tailscale netfilter modes · Tailscale Docs](https://tailscale.com/docs/reference/netfilter-modes)
- [Linux: ts-input DROP of source 100.64.0.0/10 breaks Alibaba Cloud ECS internal DNS and apt · tailscale/tailscale](https://github.com/tailscale/tailscale/issues/21249)
- [解决阿里云和 Tailscale 的 100 网段冲突的问题](https://blog.hellowood.dev/posts/resolve-alibaba-cloud-tailscale-100-network-conflict/)