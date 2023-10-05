---
layout: post
title: 项目中引入springcloud网关Gateway
excerpt: 一个小小的quicStart以及自己遇到的问题汇总
category: spring_boot
keywords: spring_boot, java
lang: zh
---

## 前言

在新公司做工已经两个月了，时间真的是快的吓人。我的主要工作是重构项目，所以也没什么适应期，不需要看老项目。随着这个新项目开发推进和合理性讨论，DDD的落地还是需要借助SpringCloud来做服务领域划分，因为我前东家用的是SpringCloud-Alibaba，所以我自己对其生态比较熟悉，所以经过讨论就打算先慢慢接入。

首先就是把注册中心(Nacos)和网关接入(Gateway)，然后服务的rpc调用框架(OpenFeign)。其实springboot相关的生态已经做的很开箱即用了，但是在引入的过程中还是遇到一些小小的问题，尤其是引入Gateway过程中花了无谓的一下午时间，现在看来只要导入依赖和设置路由配置就好了。所以特意记录一下，给大家避避坑。

我写一个简单的QuicStart，并且把项目放到[Github](https://github.com/oreoft/quickstart-gateway)上

### 项目结构

- quickstart-gateway(外层父项目)
    - demo-gateway(gateway项目)
    - demo-service(服务项目,通过Gateway访问这个项目接口)

项目结构就是如上，这里只演示通过Gateway去调用一个service应用。这个跑通了，抄到项目里面就八九不离十。里面pom文件的编写我就不多说啦



### pom坐标

设置SpringBoot的版本(这个在父模块)

```xml
<parent>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-parent</artifactId>
  <version>2.3.4.RELEASE</version>
</parent>
```

设置dependencyManagement(在父模块，规定cloud和springboot相对应的版本号)

```xml
  <properties>
    <spring-cloud.version>Hoxton.SR10</spring-cloud.version>
  </properties>
<dependencyManagement>
    <!-- 指定cloud的版本 -->
    <dependency>
      <groupId>org.springframework.cloud</groupId>
      <artifactId>spring-cloud-dependencies</artifactId>
      <version>${spring-cloud.version}</version>
      <type>pom</type>
      <scope>import</scope>
    </dependency>
  </dependencies>
</dependencyManagement>
```

Gateway我选择的版本(这个只在demo-gateway模块，代码里面我使用的dependencyManagement来管理子模块的版本号)

```xml
<dependency>
  <groupId>org.springframework.cloud</groupId>
  <artifactId>spring-cloud-starter-gateway</artifactId>
  <version>2.2.7.RELEASE</version>
</dependency>
```

Nacos我选择的版本(demo-gateway和demo-service都要引入。代码里面我使用的dependencyManagement来管理子模块的版本号)

```xml
  <dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
    <version>0.9.0.RELEASE</version>
  </dependency>
```

### 配置文件

demo-gateway模块的配置文件

```yml
server:
  port: 8081

spring:
  application:
    name: demo-gateway
  cloud:
    # nacos的配置(这个nacos.host,请换成自己的nacos地址)
    nacos:
      discovery:
        server-addr: nacos.host:8848
    # gateway的配置
    gateway:
      # 开启从注册中心动态创建路由的功能，利用微服务名进行路由
      discovery:
        locator:
          enabled: false
      routes:
      # 路由组名
      - id: service
        # lb负载均衡访问, 后面是模块的application.name
        uri: lb://demo-service
        # 匹配规则, 最好api-模块名的规范匹配
        predicates:
        - Path=/api-service/**
        # 截取访问路径的前缀
#        routes:
#          filters:
#            -StripPrefix=1


```

demo-service的配置文件

```yml
server:
  port: 8082

spring:
  # 在各注册中心中显示服务的名字
  application:
    name: demo-service
  cloud:
    # nacos的设置(这个nacos.host,请换成自己的nacos地址)
    nacos:
      discovery:
        server-addr: nacos.host:8848
```

### 测试

把上面的配好以后，其实gateway现在就可以启动了，gateway可以在代码里面进行配置(例如复杂的过滤器等)，也可以在配置文件中简单的进行一些谓词和过滤器的配置

然后我们在demo-service模块中写一个hello接口

```java
@RestController
@RequestMapping("/api-service")
public class DemoController {

  @GetMapping("/hello")
  public String judgeOk() {
    return "ok";
  }

}
```

![image-20211019233046301](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211019233046.png)



### 可能会遇到的问题速查

至此已经引入成功，这些组件都已经封装的很好了，理论上可以做到开箱即用，这里列举一些我遇到的问题。

- java.lang.NoSuchMethodError: reactor.netty.http.client.HttpClient.chunkedTransfer(Z)Lreactor/netty/http/client/HttpClient;

![image-20211019215037551](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211019215037.png)

<br>

我的推测：版本问题(springboot版本高了)，可以换``2.1.6.RELEASE``试试

- java.lang.IllegalStateException: Error processing condition on org.springframework.cloud.gateway.config.GatewayAutoConfiguration$NettyConfiguration.gatewayHttpClient

![image-20211019215506845](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211019215506.png)

<br>

我的推测：版本问题(gateway版本高了)，可以换``2.1.1.RELEASE``试试

- Parameter 0 of method modifyRequestBodyGatewayFilterFactory in org.springframework.cloud.gateway.config.GatewayAutoConfiguration required a bean of type 'org.springframework.http.codec.ServerCodecConfigurer' that could not be found.

![image-20211019225320971](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211019225321.png)

<br>

上面这个版本问题强烈建议使用``dependencyManagement``来管理。在这[官网](https://spring.io/projects/spring-cloud)找到自己springboot版本对应的cloud版本，如下图

![image-20211020212848601](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211020212848.png)

<center>左侧是cloud版本(点进去有版本，原来是英文地铁站命名)，右侧是boot版本</center>

比如我用的是2.3.4的boot版本，我看到[Hoxton](https://github.com/spring-cloud/spring-cloud-release/wiki/Spring-Cloud-Hoxton-Release-Notes)里面如下告诉我，我的2.3.x是需要用以下的组件版本。

![image-20211020213046180](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211020213046.png)

然后你在pom里面设置``dependencyManagement``，它会帮你管理成如下的版本，你只需要导入就行了不用管版本号。

![image-20211020213334390](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211020213334.png)



- 服务启动成功，但是访问报错**404**

我的推测：web依赖和webflux依赖冲突

```xml
     <!-- web依赖 -->
		<dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
      <version>${springboot.version}</version>
    </dependency>
     <!-- webflux依赖 -->
   <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-webflux</artifactId>
      <version>${springboot.version}</version>
    </dependency>
```

这个问题我实测好几遍，就是web和webflux冲突了，gateway使用的是webflux，如果你在gateway项目里面又重复引入web依赖或者gateway的父级(最有可能)就会出现这样的问题。那么解决办法就是把spring-boot-starter-web的依赖移除，但是如果是父级的话，可以考虑把这个父级依赖分别挪到对应的项目中，毕竟web模块不起服务的模块是不需要的，但是如果已经做了粒度划分实在想要排除，可以使用曲线救国实现。把下面代码添加到gateway的pom文件。

子模块重新导入web模块，并且指定test才生效，总这样就可以让编译器把这个依赖给过滤掉。如果想要排除只能这样，我试过exclusions排除web，发现没有效果，原因是exclusions只能在某个依赖里面使用，它排除的是这个依赖里面的依赖，不能排除自己项目的父级依赖

```xml
    <!-- 特殊处理，不引入父类lib -->
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
      <scope>test</scope>
    </dependency>
```

- 服务启动成功，但是访问报错**503**

排除服务刚刚启动它没来得及就被你访问了导致503后

1. 可能在nacos中没找到对应访问应用，检查一下nacos状态和配置文件里面的name
2. 看看getway的依赖是否排除了webflux，这个不能排除

![image-20211019224852952](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211019224853.png)

<br>

- 服务启动成功，但是访问报错**404**

1. 检查配置文件

![image-20211019223058086](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20211019223058.png)

<center>是否有开启注册中心创建路由</center>

<br>

```xml
 gateway:
      # 开启从注册中心动态创建路由的功能，利用微服务名进行路由
      discovery:
        locator:
          enabled: false
```

2. 如果还是不行，检查一下predicates的配置，值得注意的是添加下面的配置，会截取前面N个/路径。意思就是假如predicates: -Path=/api-service/**。然后N配置1，访问/api-service/hello。到对应service应用只有hello。

```xml
routes:
	filters:
		-StripPrefix=N(这个N是数字)
```

