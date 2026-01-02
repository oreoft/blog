---
category: tools
excerpt: Quick Fix
keywords: tools
lang: en
layout: post
title: How to Fix IDEA Not Showing the Run Dashboard
---

## Preface

I recently started working on a microservices project. Since there are a lot of services, local debugging often means starting multiple projects. I noticed my coworkers all use the dashboard to manage projects—services and ports are laid out nice and neatly. But my dashboard was completely empty. After a bunch of Googling/Baidu, I finally fixed it.

While looking for a solution, I ran into a domestic article that kept getting copied over and over—the content never changed, only the messy formatting did. What should’ve been a small issue ended up being even more confusing for anyone trying to troubleshoot it. So I’m sharing my solution here to see if it can help others.

## Steps

1. In newer versions of IDEA, the dashboard has been integrated into **Services**, but the steps are still the same.

2. If you can’t even see **Services**, double-tap the **Shift** key, type `dashboard`, then press Enter.

   ![image-20210320145642721](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320145642.png)

3. Then you’ll see it’s empty—even if you have a bunch of microservice projects, nothing shows up here. If you *do* see a lot of projects listed, congrats: just start your services and you don’t need to read further.

	![image-20210320145737604](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320145737.png)

4. If there’s no dashboard content in **Services**, it’s usually an IDEA project configuration issue. You need to add a tag to `.idea/workspace.xml` like this:

   ```xml
   <component name="RunDashboard">
       <option name="configurationTypes">
         <set>
           <option value="SpringBootApplicationConfigurationType" />
         </set>
       </option>
       <option name="ruleStates">
         <list>
           <RuleState>
             <option name="name" value="ConfigurationTypeDashboardGroupingRule" />
           </RuleState>
           <RuleState>
             <option name="name" value="StatusDashboardGroupingRule" />
           </RuleState>
         </list>
       </option>
   </component>
   ```

5. Since `.idea` is a hidden folder: on Windows, most coders usually enable showing hidden files. On macOS, showing hidden files looks kind of ugly, so people often don’t enable it. On Windows, just follow the steps below. On macOS, I used the terminal and `vim` to add it.

   ![image-20210320150119659](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320150119.png)

<center>From the project root, go into .idea, then use vim to open workspace.xml</center><br/>

![image-20210320150438895](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320150438.png)

<center>After inserting it, press esc then type :wq to save</center><br/>
6. After writing it, restart IDEA. Then open IDEA again and open this project—you’ll get the prompt below. Choose the first option: **show run***.

	![image-20210305101341878](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320151147.png)

7. Now you should be able to see the dashboard. If you still can’t, go back into `workspace.xml` and check whether the `RunDashboard` tag is there.

	![image-20210320151138794](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320151138.png)