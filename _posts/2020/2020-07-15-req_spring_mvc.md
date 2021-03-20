---
layout: post
title: SpringMVC请求注解总结
excerpt: 请求注解
category: spring_boot
keywords: spring_boot
---

## 前言

Spring MVC 通过分析处理方法的签名，将 HTTP请求信息绑定到处理方法的相应入参中，最近接手的新项目把常用信息都写到header里面，于是使用到一个@RequestHeader注解，虽然很平常，很少用到这个，突然奇想，想要总结一下。

当然Spring MVC对控制器处理方法签名的限制是很宽松的，几乎可以按喜欢的任何方式对方法进行签名然后获取参数

##  正文

工作中比较常用获取参数

- @PathVariable

  ```
  这是restful接口常用的参数，里面的value对应接口地址上面{}的部分，可以获取接口地址上面的参数
  ```

- @RequestParam

  ```
  这是原来比较常用来接受前端传参的注解，用来处理http默认content-type的编码内容
  // 默认传递的参数就是application/x-www-form-urlencoded类型
  ```
- @RequestBody

  ```
  这是现在比较流行的接受注解，一般用来处理非Content-Type: application/x-www-form-urlencoded
  编码格式的数据。最常见的当然是json啦。
  ```
- @RequestHeader

  ```
  这是我最近经常使用的注解，因为公司把用户的userid和userkey放在header作为每次请求报文必传的内容，
  所以经常使用这个注解接收
  ```
- @CookieValue

  ```
  这个用法和@RequestParam差不多，只不过取的值是cookie中的值，用起来其实很方便啦，比在代码里面取优雅很多
  ```
  
  以上大部分注解，除了有value值，还有required字段，这个默认为true，表示如果对方没有传则抛出异常，一般手动会把这个值修改成false，当然是希望我们在代码里面返回友好提示异常啦。
  