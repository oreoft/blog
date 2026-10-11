---
category: java
excerpt: Using `Optional` Elegantly for Null Checks in Java
keywords: java
lang: en
layout: post
title: Using `Optional` in Java for Elegant Null Checks
---

## Introduction

`Exception in thread "main" java.lang.NullPointerException`
I’m sure everyone runs into this a lot, or at least used to run into it a lot. When you’re new to coding, it’s totally normal to lack experience and miss some edge cases. Code that isn’t very robust is completely normal at that stage, but after getting burned a few times, you remember the lesson 😏.

Null checks are extremely common and all over project code. `Optional`, added in JDK 8, can reduce redundant code to some extent and make null checking more elegant. You’ve probably seen or heard about it in other articles. I had read other people’s posts about it too, and I felt like they made sense, but after a whole lot of explanation, I still didn’t really know how to use it. Later, I saw coworkers using it in real code, started using it myself, and then went back to read the source code and other articles. Suddenly, everything clicked. So now I believe it’s better to become an API engineer first, and only then dive into the internals.

## A Simple Explanation

Looking at the source code of `Optional` (hereafter referred to as `opt`), `opt` is basically a container. This container can hold your object, turning it into an `opt` object. Then you can use `opt` methods to do null checks or other operations, and finally either extract your object from `opt` or continue with other logic. That might sound a bit fancy, but what I really want to tell you is this: to create an `opt` object, you need to put your variable into one of `opt`’s static methods. `Optional` provides three methods:

![image-20210408091539829](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408091539.png)

<center>The three static methods of Optional</center>



Usually, we create an `Optional` container like this:

```java
Integer num = null;
// Usually we just chain the call directly instead of assigning this opt to a reference
Optional<Integer> optNum = Optional.ofNullable(num);
```

## API Engineer Advanced Level

### Creating an opt object

As you can see above, you can use `of()` / `ofNullable()` in `opt` to wrap the variable you want to null-check. `empty()` creates an empty `Optional` object. Emmm... for me, it’s not that useful. Honestly, this probably should have been a private method, since it’s mostly called internally.

So what’s the difference between `of` and `ofNullable`? Let me give the conclusion first: I generally don’t use `of` either. Just look at the source code. `of` eventually calls `Objects.requireNonNull`. If you’re familiar with it, you’ll know right away—this is basically the source of an NPE.

```java
    public static <T> T requireNonNull(T obj) {
        if (obj == null) // If it's null here, it directly throws a NullPointerException
            throw new NullPointerException();
        return obj;
    }
```

Now let’s look at the source code of `ofNullable`:

```java
    public static <T> Optional<T> ofNullable(T value) {
        return value == null ? empty() : of(value);
    }
```

Obviously, it’s pretty clear which one to use. `ofNullable` performs a check first. If the value is `null`, it calls `empty()` to create an empty `opt` object. If it’s not `null`, it calls `of()` to create an `opt` container and wrap your value.



By the way, if you’re using IDEA, you can use the postfix shortcut I mentioned before to wrap your variable into `opt`. The trigger is `.opt`.

![2021-04-08 09.27.25](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408092851.gif)

<center>This comes built into IDEA, no need to add it yourself. Give it a try.</center>



### Provide a default value if null

```java
Optional.ofNullable(num)
```

Now that we’ve reached this step, in most cases after checking for null, if we find the variable is null, we’ll give it an initial value so the following process can continue safely.

Here you can use the `orElse()` method. What it does is: if this `opt` is `empty` (don’t forget, if your value is `null`, the `opt` class will create an `empty` object), then it returns the argument you passed into `orElse`. Otherwise, it extracts and returns the variable wrapped inside the `opt` container. Show code:

```java
        Integer num = null;
        // Is num null? If not, result is its own value; if yes, result is 1
        Integer result = Optional.ofNullable(num).orElse(1);
        System.out.println(String.format("The value of result is %d", result));

输出结果为 result的值是1
```

![image-20210408093557434](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408093557.png)

<center>There are similar methods too—feel free to explore them yourself</center>



### Whether it exists

Besides assigning a default value when null, there are other null-checking needs too. For example, maybe I just want to know whether it’s null. Of course, we can directly use `Objects.isNull()` or just `==` to do that, but `opt` also provides a method for this: `isPresent`. It feels especially nice to use when you have a long chain of method calls and need this kind of check at the end.

```java
        Integer num = null;
        // Check whether this opt object exists (more accurately, whether it is empty)
        boolean present = Optional.ofNullable(num).isPresent();
        System.out.println(present);
输出结果为 false
```



### What to do if it exists

Pay attention here: above we talked about `isPresent`, and now we’re going to talk about `ifPresent`. Don’t mix up `is` and `if`.

In most cases, after checking whether a value is null, we still want to execute some logic. `opt` provides the `ifPresent` method, where you pass in a `Consumer` lambda expression. This is basically a fixed usage pattern. Also note: if the object wrapped inside your `opt` is a `List`, then the lambda parameter inside `ifPresent` is that whole `List`, not each individual element inside it.

```java
// Simulate fetching Xiaoming's information from the database, intentionally not telling you Xiaoming's age
student.put("name", "小明");
student.put("age", UNKNOWN);
// Check whether Xiaoming's age is null; if not, determine whether Xiaoming is an adult
Optional.ofNullable(student.get("age")).
  ifPresent(e -> student.put("isAdult", UNKNOWN >= 18 ? 1 : 0));
```



## Final Thoughts

![Optional 类里所有的方法和属性](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408091744.png)

<center>All methods and fields inside it</center>

But the methods I introduced above are the ones I use frequently at work. I’d suggest getting comfortable with these first, and then taking a look at the other methods inside `Optional`. Actually, there isn’t much in `Optional`, and reading through the source code doesn’t take much time either.