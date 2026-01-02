---
category: java
excerpt: 'Translate excerpt to English: Using `Optional` in Java for Elegant Null
  Checks'
keywords: java
lang: en
layout: post
title: Elegantly Handling Null Checks in Java with Optional
---

## Preface

`Exception in thread "main" java.lang.NullPointerException`  
I’m sure you’ve run into this a lot—or at least used to—because early on, when you’re still inexperienced and not thinking things through, it’s totally normal for your code to not be that robust. But after getting burned a few times, you learn your lesson 😏.

Null checks are super common and basically everywhere in project code. Optional, added in JDK 8, can reduce some redundant code and make null checking a bit more elegant. You’ve probably seen or heard about it in other articles. I actually read a bunch of those too and felt like they made sense, but they were so long-winded that after finishing I still didn’t really know how to use it. Later, I saw coworkers using it in real code, started following along, then went back to read the source and other posts—and it suddenly clicked. So now I believe: become an “API engineer” first, then go dig into the internals.

## A quick explanation

From Optional’s (hereafter “opt”) source code, opt is basically a container. You can put your object into it so it becomes an opt object, then use opt’s methods to do null checks or other operations, and finally pull your object back out (or do other logic). That might sound a bit fancy, but what I really want to tell you is: to create an opt object, you put your variable into Optional’s static methods. Optional provides three methods:

![image-20210408091539829](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408091539.png)

<center>Three static methods of Optional</center>



Usually we create an Optional container like this:

```java
Integer num = null;
// Usually we just chain calls directly and won’t keep a reference to this opt
Optional<Integer> optNum = Optional.ofNullable(num);
```

## Leveling up as an API engineer

### Creating an opt object

As you can see above, using `of()` / `ofNullable()` in opt lets you wrap the variable you want to null-check. `empty()` creates an empty Optional object. Umm... for me it’s not that useful—honestly this should be a private method, because only internal code should call it.

So what’s the difference between `of` and `ofNullable`? Here’s the conclusion first: I generally don’t use `of` either. Just look at the source—`of` eventually calls `Objects.requireNonNull`. If you’re familiar with it, you know: isn’t this basically the NPE source?

```java
    public static <T> T requireNonNull(T obj) {
        if (obj == null) // if it's null here, it throws NPE directly
            throw new NullPointerException();
        return obj;
    }
```

Now let’s look at `ofNullable`:

```java
    public static <T> Optional<T> ofNullable(T value) {
        return value == null ? empty() : of(value);
    }
```

Pretty obvious which one to use. `ofNullable` checks first: if it’s `null`, it calls `empty()` to create an empty opt object; if it’s not `null`, it calls `of()` to create an opt container and wrap your value.



Also, if you’re using IntelliJ IDEA, you can use the postfix shortcut I mentioned before to wrap your variable into an opt. The trigger is `.opt`.

![2021-04-08 09.27.25](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408092851.gif)

<center>This comes built-in with IDEA—no need to add it yourself. Give it a try</center>



### Provide a default value when null

```java
Optional.ofNullable(num)
```

Now we’re at this step. Usually after a null check, if the variable is null, we’ll give it an initial value so it can safely continue through the rest of the flow.

Here you can use `orElse()`. This method means: if this opt is `empty` (don’t forget—if your value is `null`, opt will create an `empty` object), then return the argument you pass into `orElse`. Otherwise, it takes out the value wrapped inside the opt container. Show code:

```java
        Integer num = null;
        // whether num is null; if not, result is its own value; if yes, result is 1
        Integer result = Optional.ofNullable(num).orElse(1);
        System.out.println(String.format("result的值是%d", result));

输出结果为 result的值是1
```

![image-20210408093557434](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408093557.png)

<center>Similar features—feel free to explore on your own</center>



### Whether it exists

Besides providing a default value when null, you might have other needs during null checking—for example, you just want to know whether it’s null. Sure, we can do that with `Objects.isNull()` or `==`, but opt also provides a method (`isPresent`). Usually after a long chain of calls, having this is pretty satisfying.

```java
        Integer num = null;
        // check whether this opt object exists (more precisely, whether it's empty)
        boolean present = Optional.ofNullable(num).isPresent();
        System.out.println(present);
输出结果为 false
```



### What to do if it exists

Pay attention: above was `isPresent`, now we’re talking about `ifPresent`. Don’t mix up `is` and `if`.

Most of the time, after null checking, we still want to execute some logic. opt provides `ifPresent`, where you pass in a Consumer lambda. This is basically a standard pattern. Note: if the object wrapped in your opt is a list, then the lambda parameter in `ifPresent` is the entire list, not each element inside the list.

```java
// Simulate fetching Xiaoming's info from the database; intentionally not letting you know his age
student.put("name", "小明");
student.put("age", UNKNOWN);
// Check whether Xiaoming's age is null; if not null, determine whether he's an adult
Optional.ofNullable(student.get("age")).
  ifPresent(e -> student.put("isAdult", UNKNOWN >= 18 ? 1 : 0));
```



## Afterword

![](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210408091744.png)

<center>All methods and fields inside</center>

But the methods I covered above are the ones I use most often at work. I’d recommend getting comfortable with these first, then taking a look at the rest of Optional’s methods. Optional doesn’t actually contain much—reading the source won’t take long either.