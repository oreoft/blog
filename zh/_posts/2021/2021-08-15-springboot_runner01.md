---
layout: post
title: Springboot的Runner接口
excerpt: 配置Springboot启动自动执行业务
category: spring_boot
keywords: java, spring_boot
lang: zh
---

## 前言

最近面试真的学到很多东西，也遇到很多非常亲切的面试官，一些开放性问题在interview的过程中我回答的欠考虑或者不成熟的地方都值得我下去思考很久。也能接触到一些自己知识盲区，比如我今天想分享的SpringBoot的Runner接口，这是在一场面试中其中一个小问题，面试官说想要在SpringBoot启动以后加入一些自动执行的逻辑应该怎么做，我没答上来。这个可能是对方业务中经常用到的一个功能然后就当考题给候选人作为考察点了，确实自己实际开发中没有过使用，平时了解的也比较少。

下来以后自己查资料发现Runner接口可以做到类似的功能，知识真的在不断地积累，我觉得这个功能挺好的，以后如果我有类似的需求我就知道可以这样处理了，因为启动以后自动执行一些逻辑还是比较常见的，例如一些初始化的逻辑。我自己项目中有一些启动的时候需要提前把数据加载到JVM内存里面的操作，不过我是用Bean的afterPropertiesSet或者构造器初始化的，其实也可以统一在这里处理。



## Runner类

``org.springframework.boot``包下一共有两个Runner接口，这两个接口都有一个run方法，其实使用方法特别简单，你可以把你的bean继承这其中一个Runner，然后实现run方法就好啦。

下面详细介绍一下，这两个Runner接口，里面没啥东西，并且都是函数式接口(记住，后面有彩蛋)

第一个叫 ApplicationRunner

第二个叫 CommandLineRunner

```
@FunctionalInterface
public interface CommandLineRunner {

   /**
    * Callback used to run the bean.
    * @param args incoming main method arguments
    * @throws Exception on error
    */
   void run(String... args) throws Exception;

}

@FunctionalInterface
public interface ApplicationRunner {

	/**
	 * Callback used to run the bean.
	 * @param args incoming application arguments
	 * @throws Exception on error
	 */
	void run(ApplicationArguments args) throws Exception;

}
```

### 两者的区别

两者区别第一点就是run方法的入参上: 

```ApplicationRunner```的入参是一个String。```CommandLineRunner```的入参是一个可变长的String(相当于数组)。也就是一个和多个的区别吧，这个参数是java -jar中启动java程序的时候传入的参数，也就是如果你传入多个参数你应该使用```CommandLineRunner```，如果你只传入一个参数使用哪个都可以啦。就我经验现在大家java写后端居多，在命令上传参应该不常见吧。

下面看一下源码来解释一下，从Springboot的入口```SpringApplication.run```一直跟到实现类的run方法可以看到，在322行这里开始执行所有 Runner 运行器

![image-20210815224833541](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210815224833.png)

<center>springboot版本2.3.7</center>

<br>

然后这个方法的代码量也非常少，我就直接帖上来了

```java
private void callRunners(ApplicationContext context, ApplicationArguments args) {
   List<Object> runners = new ArrayList<>();
   // 这里是添加的ApplicationRunner
   runners.addAll(context.getBeansOfType(ApplicationRunner.class).values());
   // 然后串行添加CommandLineRunner
   runners.addAll(context.getBeansOfType(CommandLineRunner.class).values());
  // 这里会排个顺序，但是默认的话是按照添加顺序
   AnnotationAwareOrderComparator.sort(runners);
   for (Object runner : new LinkedHashSet<>(runners)) {
     // 注意，这里的args就是外层run方法的args，也就是java-jar传入的参数

      if (runner instanceof ApplicationRunner) {
         callRunner((ApplicationRunner) runner, args);
      }
      if (runner instanceof CommandLineRunner) {
         callRunner((CommandLineRunner) runner, args);
      }
   }
}
```

所以第二个区别就是在执行顺序上，先添加ApplicationRunner然后再添加CommandLineRunner，再不设置优先级的情况下，模式是先执行ApplicationRunner的方法的。



## 代码实战一下

1. 我们先分别实现一下```ApplicationRunner```和```CommandLineRunner```看一下效果

#### 分别先测试输出结果

二话不说，直接创建一个新的类，然后实现ApplicationRunner，实现run方法，run方法里面很简单，就是输出一句话，我们先看看springboot启动以后会不会输出。这里要注意一点，你必须把你的这个类添加到spring容器当中，也就是要加上@Component，不然是不会生效的。

```java
@Component
public class MyRunner01 implements ApplicationRunner {
    @Override
    public void run(ApplicationArguments args) throws Exception {
        System.out.println("我是ApplicationRunner");
    }
}
```

![image-20210815225846337](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210815225846.png)

<center>输出结果在springboot启动后输出成功</center>

<br>

然后我们再试试CommandLineRunner，什么都不变，就把刚刚的抄一遍就好

```java
@Component
public class MyRunner02 implements CommandLineRunner {
    @Override
    public void run(String... args) throws Exception {
        System.out.println("我是CommandLineRunner");
    }
}
```

![image-20210815230042726](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210815230042.png)

<center>也是成功输出了</center>



#### 两个一起开启，同时执行

创建了两个类，他们可以同时输出，并且``ApplicationRunner``在前面，因为上面我刚刚说了，他们addall的顺序就是``ApplicationRunner``在前面，所以它先执行。

```java
@Component
public class MyRunner01 implements ApplicationRunner {
    @Override
    public void run(ApplicationArguments args) throws Exception {
        System.out.println("我是ApplicationRunner");
    }
}

@Component
public class MyRunner02 implements CommandLineRunner {
    @Override
    public void run(String... args) throws Exception {
        System.out.println("我是CommandLineRunner");
    }
}
```

![image-20210815230314010](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210815230314.png)

<center>输出结果</center>

#### 如何设置优先级

那么很常见的场景就是我就是想让CommandLineRunner优先输出因为我有很多指令参数需要处理，或者是我相同的ApplicationRunner有很多，我业务场景顺序敏感需要对他们进行链式执行。那我们刚刚也看到启动源码中其实有对它们进行优先级处理的排序。

两个办法，一个是再实现ORdered接口，还有一个是使用Order注解。当然，人生苦短，我选注解。

```java
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.TYPE, ElementType.METHOD, ElementType.FIELD})
@Documented
public @interface Order {

   /**
    * The order value.
    * <p>Default is {@link Ordered#LOWEST_PRECEDENCE}.
    * @see Ordered#getOrder()
    */
   int value() default Ordered.LOWEST_PRECEDENCE;

}
```

注解有一个属性，就是value，这个value是一个int数字，这个数字决定了优先级顺序，越小就越靠前(默认值是Integer的最大值)。比如我以刚刚两个为例，我把实现``CommandLineRunner``的类order变成1，实现``ApplicationRunner``的order为2。

结果就是order更小的优先执行了，所以如果你有多个Runner可以使用这个方式来按照你期望的串行化执行。

```JAVA
@Component
@Order(2)
public class MyRunner01 implements ApplicationRunner {
    @Override
    public void run(ApplicationArguments args) throws Exception {
        System.out.println("我是ApplicationRunner");
    }
}

@Component
@Order(1)
public class MyRunner02 implements CommandLineRunner {
    @Override
    public void run(String... args) throws Exception {
        System.out.println("我是CommandLineRunner");
    }
}
```

![image-20210815231118568](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210815231118.png)

<center>结果符合预期</center>

## 进阶彩蛋

前面的内容网上文章都是其实都是这么写的，反正一些博客都抄来抄去，你看别的博客也能看懂，只不过我更加啰嗦一点，结合源码多说了一点。

但是真的项目里面会这么写吗？一个类一个类的实现一般写demo会这么做，在实际项目中可能还是会在一个Component下面。

也就是在一个Component下用方法返回一个bean，注入到ioc容器当中，而不是把一个类继承Runner接口然后作为Component注入ioc容器当中，这样的好处就是用一个类统一管理。当然哈，也不能一棍子打死，我这样处理适用于逻辑比较少的业务。具体代码如下

```java
@Component
public class MyRunner03 {
    @Bean
    public ApplicationRunner app01() {
        return e -> System.out.println("我是app01");
    }

    @Bean
    public ApplicationRunner app02() {
        return e -> System.out.println("我是app02");
    }

    @Bean
    public CommandLineRunner cmd01() {
        return e -> System.out.println("我是cmd01");
    }

    @Bean
    public CommandLineRunner cmd02() {
        return e -> System.out.println("我是cmd02");
    }

}
```

![image-20210815232217355](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210815232217.png)

<center>执行结果</center>

<br>

其中在@bean上面也可以使用@order注解来控制顺序，然后这样整体方便管理一些，看起来比较简介的原因就是这里使用了lambda函数接口，这也是我文中开头提到这两个Runner接口都是函数式接口，可以不用实现使用lambda的话方便一些。



## 后言

知识盲区-1
