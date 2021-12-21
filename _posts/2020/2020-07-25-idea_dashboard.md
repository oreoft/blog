---
layout: post
title:  IDEA 无法显示 Run Dashboard 的解决方法
excerpt:  快速解决
category: tools
keywords: tools
---

## 前言

最近开始接触微服务的项目，项目很多有时候本地调测需要启动多个项目，看到同事都是使用dashboard管理项目，服务和端口排列的整整齐齐。但是我dashboard里面啥都没有，一顿百度最后解决问题，在找解决方法的过程中看到国内一篇文章抄来抄去内容都不变唯一变动的就是乱七八糟的排版，本来很小的问题反而给找问题者带来更大迷惑性的困扰，所以我分享了一下我的解决办法，看能不能帮助到大家。

## 步骤

1. 新版的idea把dashboard已经整合到services里面了，但是操作步骤依然是不变的

2. 如果你连services都看不到，双击一下shift键然后输入dashboard，然后回车进入

   ![image-20210320145642721](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320145642.png)

3. 然后看到里面都是空的，尽管你有很多微服务的项目，这里都不显示，然后如果你看到里面有很多项目，那恭喜你直接启动服务吧，不需要往下看了。

	![image-20210320145737604](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320145737.png)

4. services里面没有dashboard内容，一般是idea的项目问题，需要在.idea文件夹下的workspace.xml加入一个标签，标签如下

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

5. 因为.idea是隐藏文件，win下各位coder一般会把隐藏文件打开，但是mac下面显示隐藏文件比较难看，所以大家一般都没有打开，win按照下面直接操作就好，mac我是使用终端去操作vim添加的。

   ![image-20210320150119659](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320150119.png)

<center>项目根目录进入idea，然后vim进入这workspace.xml</center><br/>

![image-20210320150438895](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320150438.png)

<center>插入后，按esc然后输入:wq，保存</center><br/>
6. 写入后重启idea，然后再打开idea并且打开这个项目会提示下列提示，选择第一个show run***

	![image-20210305101341878](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320151147.png)

7. 然后你就可以看到dashboard了，如果你还是没看到，请再进workspace.xml检查是否有RunDashboard这个标签。

	![image-20210320151138794](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210320151138.png)
