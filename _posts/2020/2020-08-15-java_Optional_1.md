---
layout: post
title:  java使用Optional优雅判空
excerpt: java使用Optional优雅判空
category: java
keywords: java
lang: zh
---

## 前言

`Exception in thread "main" java.lang.NullPointerException`
大家肯定经常遇到或者说曾经经常遇到，因为在写代码初期因为经验不足，考虑不周。写的代码并不是非常健壮是非常正常的，但是吃过几次亏就长记性了😏。

变量判空是非常常见，并且充斥在项目代码里面。jdk8新增的Optional在某种程度上可以减少冗余代码的产生，让你判空更加优雅。你肯定在其他文章中看过或者了解过，其实我原来也看过别人写的文章，觉得别人写的有道理，但是巴啦啦一大堆，看完还是不知道怎么用，后来在工作中看到同事代码用到也跟着使用，然后再去翻源码和看别人的文章，顿时就豁然开朗。所以我现在认为先成为一名api工程师再去干原理。

## 简单讲述

从OPtional（下称opt）的源码来看，opt属于一个容器，这个容器可以装你的对象，从而让他变成opt对象，使用opt的方法对他进行判空或者其他操作，最后再从opt中把你的对象取出来或者进行其他逻辑。这么听可能觉得花里胡哨，我这里其实想告诉你生成opt对象需要把你的变量对象放到opt的静态方法中，Optional提供三个方法

![image-20210408091539829](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408091539.png)

<center>Optional的三个静态方法</center>



一般我们会这样生成一个Optional容器

```java
Integer num = null;
// 一般我们会直接链式调用，不会把这个opt用引用指向
Optional<Integer> optNum = Optional.ofNullable(num);
```

## API工程师进阶

### 生成opt对象

上面可以看到，使用opt里面的of()/ofNullable()可以把自己需要判空的变量放进去，其中empty会生成一个空的Optional对象，emmm....对我而言没啥用，其实这个应该是private方法，因为只有内部才会调用。

of/ofNullable有啥区别呢。先说结论，of我一般也不会使用，直接看一下源码，of最终会调用Objects的requireNonNull这个方法，熟悉的同学明白，这不就是npe的源码吗

```java
    public static <T> T requireNonNull(T obj) {
        if (obj == null) // 这里如果为空则直接报空指针了
            throw new NullPointerException();
        return obj;
    }
```

我们再看看ofNullable的源码

```java
    public static <T> Optional<T> ofNullable(T value) {
        return value == null ? empty() : of(value);
    }
```

显然，用谁自然不用说了，ofNullable中会进行一个判断，如果为null则会调用empty方法，生成一个空的opt对象。如果不为null会调用of方法生成opt容器把你的值装起来。



这里告诉大家，如果大家使用的是idea，可以使用我原来说的postfix快捷方法把你的变量装进opt中。激活操作为.opt

![2021-04-08 09.27.25](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408092851.gif)

<center>这个idea自带的，不用自己添加，大家试试吧</center>



### 若为空给默认值

```java
Optional.ofNullable(num)
```

现在我们到了这一步了，一般我们判空以后，发现变量是空会给它一个初值，让它可以安全的走接下里的流程。

这里可以使用orElse()方法，这个方法是说如果这个opt是empty（别忘记了，你的值如果是null，opt类会生成一个empty对象），则使用你传入在orElse方法的参数返回。否则把装在opt容器里面的变量取出来。show code

```java
        Integer num = null;
        // num是不是null, 如果不是result为它本身的值, 如果是则为1
        Integer result = Optional.ofNullable(num).orElse(1);
        System.out.println(String.format("result的值是%d", result));

输出结果为 result的值是1
```

![image-20210408093557434](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408093557.png)

<center>类似功能，大家可以自行探索</center>



### 是否存在

除了为空给默认值，大家在判空还有一些其他需求，比如我想知道是否为空。当然啦，我们可以直接使用Objects.isNull()或者直接==来做到，不过opt也给我们提供了方法(isPresent，一般很长的链式调用以后有这个需求使用起来会觉得很爽.

```java
        Integer num = null;
        // 判断这个opt对象存不存在(准确来说是不是empty)
        boolean present = Optional.ofNullable(num).isPresent();
        System.out.println(present);
输出结果为 false
```



### 如果存在怎么做

注意了，上面是isPresent，现在要讲一个ifPresent， 注意is和if不要弄混了。

大部分情况我们对值判空以后还是要是执行一套逻辑，opt给我们提供了ifPresent的一个方法，里面传入一个consumer的lambda表达式，这个应该是固定写法了，注意如果你opt里面包裹的对象是一个list，你ifPresent里面lambda的入参也是这一整个list，而不是里面每一个list的元素

```java
// 模拟从数据库里面查出小明的信息, 特意不让你知道小明的年龄
student.put("name", "小明");
student.put("age", UNKNOWN);
// 看小明年龄是不是为空, 如果不为空判断一下小明是否成年
Optional.ofNullable(student.get("age")).
  ifPresent(e -> student.put("isAdult", UNKNOWN >= 18 ? 1 : 0));
```



## 后言

![](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408091744.png)

<center>里面所有的方法和属性</center>

但是我上面讲的方法是工作中经常会使用到的，建议先把这些方法用熟练然后再去看一下Optional里面的方法，其实Optional里面东西很少，看一下源码也花不了多少时间。