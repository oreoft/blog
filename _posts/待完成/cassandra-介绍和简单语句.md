---
layout: post
title: MacOS自定义快捷键一键休眠
excerpt: 找了很久终于找到优雅的方式了
category: other
keywords: other, macos
---

## 前言

```
public static void main(String[] args) {
    // 我们需要做一个对一个数进行复杂的处理, 例如先放大2.5倍, 然后把它变成字符串后面加一个'分'字
    List<Integer> list = Lists.newArrayList(1, 2, 3, 4, 5);
    // 我们有三种方法实现 1-代码写到方法里面, 2-在循环里面直接写代码, 3-把代码传入循环里面

    // 第一种, 直接把代码写在循环里面, 这样不能复用, 并且如果代码复杂一点, 这个结构就会非常的不清晰, 简单代码量不需要复用比较适合这种
    List<String> collect = list.stream().map(num -> (num * 2.5) + "fen").collect(Collectors.toList());
    Function<Integer, String> fun = num -> (num * 2.5) + "fen";
    // 第二种, 把这个定义代码定义出来, 提升到抽象层面可以简单复用, 简单代码量需要复用比较适合这种, 主要写起来比较简单
    List<String> collect2 = list.stream().map(fun::apply).collect(Collectors.toList());
    // 第三种, 如果业务复杂并且有多出复用情况, 应当把定义方法调用使用, 记得取一个见名知意的好方法.
    List<String> collect1 = list.stream().map(Test::convert).collect(Collectors.toList());

}
public static String convert(int num) {
    return (num * 2.5) + "fen";
}
```

## 教程

### 方法一-使用系统一键锁屏

123123

### 方法二-使用特殊键盘

123123


### 方法三-使用第三方软件

23123
### 方法四-使用自动操作（推荐）

123123

## 参考

123