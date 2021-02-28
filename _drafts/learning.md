## java

### [线程](https://mp.weixin.qq.com/s/dRqLZG7eev87hda9ohlJrA)

![img](https://mmbiz.qpic.cn/mmbiz_png/TNUwKhV0JpRnhtnn45ABicYviaQNwW6IgFM7vNokicx6NlzsuSnLHJznz7nhb4awwx2rqxyZmtCqvhfGKBrvxWEIw/640?wx_fmt=png)

- 第一种方法使用多线程(集成Thread)

在类中继承Thread然后重写run方法,在run方法中写要进行多线程的业务, 然后在调用处new这个对象调用

```java
// 这里也有了两种方式
MyThread myThread = new MyThread(); // 然后直接调用
Thread t1 = new Thread(myThread) // 然后使用t1,这样做的好处就是如果有t2,t1和t2使用的是同一个对象,共享数据
```

- 第二种方法使用多线程(实现Runnable)

在类中实现Runnable并且实现run方法, 在run方法中重写多线程的业务, 然后在调用出new这个对象调用

```java
MyThread mt1 = new MyThread("") ;    // 实例化对象 
MyThread mt2 = new MyThread("") ;    // 实例化对象 
mt1.start() ;   // 调用线程主体 
mt2.start() ;   // 调用线程主体 
```



- 如何获得当前执行的线程

> Thread.currentThread().getName();

- Thread中run和start的区别,

> start是多线程调用, 并行执行. 而run是作为普通方法调用, 仅仅是串行执行. 

 - 线程池核心类

> 在 java.util.concurrent 包中我们能找到线程池的定义，其中 ThreadPoolExecutor 是我们线程池核心类

- 打开线程池

> 使用execute()或者submit()两种方式,前者无返回值,后者会返回future对象可以用来判断是否成功

- 关闭线程池

> shutdown()或者shutdownNow(),前者中断没有在执行的任务,然后设置线程池为shutdown,后者先把线程池设置成stop,然后尝试停止所有正在执行的的任务并返回等待列表

- Synchronized和CAS

>CAS属于乐观锁, Synchronized属于悲观锁

### [集合](https://mp.weixin.qq.com/s/e-EYz1ez9pFYmnSWAg69Pg)

- HashMap

>大方向上，HashMap整体是一个哈希表, 里面是一个**数组**，然后数组中每个元素是一个**单向链表**, jdk8以后元素超过8个链表会变成红黑树
>
>容量:当前数组的容量
>
>负载因子: 哈希表装满程度, 如果值越大则元素越多冲突的可能越多.
>
>扩容的伐值: 容量乘以负载因子, 容纳多少个元素数组会库容.jdk8以前每次扩容直接2倍

- ArrayList和LinkedList的区别

> 前者是数组实现的,后者是链表实现的.所以前者有索引随机读取好一些,后者有指针增删查效率高一些.

- HashMap和Hashtable的区别

> HashMap线程不安全,Hashtable线程安全,但是会堵塞其他线程,性能不是很好.最好的替代品是ConcurrentHashMap
>
>  ConcurrentHashMap 是 JDK 1.5 添加的新集合，用来保证线程安全性，提升 Map 集合的并发效率。1.8以前ConcurrentHashMap 使用了 Segment的概念，默认有 16 个 Segment，Segment里面依然还是数组 + 链表的数据结构，相当于给 HashMap 分桶处理了。因每次只会锁住其中一个 Segment，所以性能非常好。但是1.8放弃使用了分段锁，是因为多个分段锁浪费内存空间，竞争同一个锁的概率非常小，分段锁反而会造成效率低。放弃了分段锁而是用了 Node 锁，减低锁的粒度，提高性能，并使用 CAS 操作来确保 Node 的一些操作的原子性，取代了锁.
>
> ConcurrentHashMap 关键词就是CAS乐观锁, 1.8放弃分段锁segment, 

- Collections.sort 和 Arrays.sort 的实现原理

> Collection.sort 是对 list 进行排序其调用了list.sort()方法,而list.sort()方法调用了Arrays.sort()方法，Arrays.sort 是对数组进行排序。
>
> 因此Collections.sort 方法底层就是调用的 Array.sort 方法

-  Collection 与 Collections 的区别是什么

> Collection 是 Java 集合框架中的基本接口，如 List 接口也是继承于它
>
> Collections 是 Java 集合框架提供的一个工具类，其中包含了大量用于操作或返回集合的静态方法(如sort,max,min,reverse,indexofsublist)。

-  hashset 为什么元素都不能重复

>因为hashset底层是一个哈希表,存进去会生成hashcode和equals方法判断是否重复

- java的LinkedList是双向链表, HashMap拉链法的是单向链表
- HashMap和ArrayList的扩容机制

> HashMap增加元素的时候判断是否达到阈值,如果达到阈值则选择扩容原来跌两倍,然后拷贝元素
>
> ArrayList增加元素的时候判断是否越界,如果越界则计算出新的扩容数组size然后实例化(扩容一般是扩容1.5倍),把原来的元素再拷过去

- 为什么1.8要用红黑树

> java8不是用红黑树来管理hashmap,而是在hash值相同的情况下(且重复数量大于8),用红黑树来管理数据。
> 红黑树相当于排序数据。可以自动的使用二分法进行定位。性能较高。

- Map和List的默认容量

> HashMap的默认初始容量是16, ArrayList的初始容量是10

- 如何保证集合不被修改

>Collections里面有一个unmodifiableCollection函数,使用Collections.unmodifiableCollection(Collection c)创建的集合,不能被修改

- 红黑树的特点？

>每个节点定位红色或者黑色。
>
>根节点是黑色。
>
>每个叶子节点（NIL）是黑色。[注意：这里叶子节点，是指为空 (NIL 或 NULL) 的叶子节点！]
>
>如果一个节点是红色的，则它的子节点必须是黑色的。
>
>从一个节点到该节点的子孙节点的所有路径上包含相同数目的黑节点。

- Set里面的元素是不能重复的使用的是==还是equals()

> 使用的是equals(), ==是比较地址,而equals在object里面和==等同,但是一般我们会根据实际的业务场景来重写它

- 1.7和1.8的hashmap有什么区别

> ![img](https://mmbiz.qpic.cn/mmbiz_png/sMmr4XOCBzHTXzzpaoia3tmfmZWFoOAsp0HQfUGaj9RHydC0fiaQgtRX3WFh6upR7xuCA73ic5VWicXXoIiacryw8UA/640?wx_fmt=png)

- 在ArrayList加入1w条数据,应该怎么提高效率

>首先保证插入的元素不会频繁增删, 不然不会首选ArrayList, 确定使用的话应当在初始化的时候给定1w的初始值,避免频繁扩容

- HashMap 的扩容机制

>HashMap 的扩容机制，Hashmap 的扩容中主要进行两步，第一步把数组长度变为原来的两倍，第二部把旧数组的元素重新计算 hash 插入到新数组中，jdk8 时，不用重新计算 hash，只用看看原来的 hash 值新增的一位是零还是 1，如果是 1 这个元素在新数组中的位置，是原数组的位置加原数组长度，如果是零就插入到原数组中。扩容过程第二部一个非常重要的方法是 transfer 方法，采用头插法，把旧数组的元素插入到新数组中。

- HashMap 大小为什么是 2 的幂次方

>效率高 + 空间分布均匀

## jvm[基础](https://mp.weixin.qq.com/s/eNpHYG9T5DIdh7QNpLg4dQ)

test

## springboot

### [ioc](https://mp.weixin.qq.com/s/hm7ywz_JBu0chupAvJCsWA)

https://www.cnblogs.com/superjt/p/4311577.html

![image-20201014100822852](C:\Users\oreoft\AppData\Roaming\Typora\typora-user-images\image-20201014100822852.png)

- ioc的容器(BeanFactory和ApplicationContext)

> - 对于BeanFactory来说，对象实例化默认采用延迟初始化。通常情况下，当对象A被请求而需要第一次实例化的时候，如果它所依赖的对象B之前同样没有被实例化，那么容器会先实例化对象A所依赖的对象。这时容器内部就会首先实例化对象B，以及对象 A依赖的其他还没有实例化的对象。这种情况是容器内部调用getBean()，对于本次请求的请求方是隐式的。
>
> - ApplicationContext启动之后会实例化所有的bean定义，但ApplicationContext在实现的过程中依然遵循Spring容器实现流程的两个阶段，只不过它会在启动阶段的活动完成之后，紧接着调用注册到该容器的所有bean定义的实例化方法getBean()。这就是为什么当你得到ApplicationContext类型的容器引用时，容器内所有对象已经被全部实例化完成。
> - ![img](https://img-blog.csdn.net/2018051314445763?watermark/2/text/aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3E5ODIxNTE3NTY=/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70)

- iocbean的生命周期

> 先注册bean使用configuration等注解表名这个类已经被ioc接管,然后里面可以定义一些方法init或者destory
>
> 两种方式,第一种
>
> ```java
> // 要创造的类中写init和destory方法
> //然后在创造这个类的bean中注解表名方法
>     @Bean(initMethod = "init", destroyMethod = "destory")
>     public Car car() {
>         return new Car();
>     }
> ```
>
> 第二种
>
> ```java
> // 在创造的类中加入init和destory方法,并且注解,下次创造的这个类的时候就会自动执行
> public class Dog {
>     public Dog() {
>         System.out.println("dog constructor.....");
>     }
> 
>     //在Construct之后执行
>     @PostConstruct
>     public void init() {
>         System.out.println("dog @PostConstruct .......");
>     }
> 
>     //在destory执行之前
>     @PreDestroy
>     private void destoyr() {
>         System.out.println("dog @PreDestroy.......");
>     }
> }
> ```

### [aop](https://mp.weixin.qq.com/s/RZf0sCkWSGweh_1zAqwvxA)

```java
/**
 * 前置增强
 */
public interface BeforeAdvice {
    public void before();
}
```

```java
public interface AfterAdvice {
    public void after();
}
```

```java
package demo3;

import com.sun.org.apache.regexp.internal.RE;
import org.junit.After;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * ProxFactory用来生成代理对象
 * 它需要所有的参数：目标对象，增强，
 * Created by Yifan Jia on 2018/6/5.
 */

/**
 * 1、创建代理工厂
 * 2、给工厂设置目标对象、前置增强、后置增强
 * 3、调用creatProxy()得到代理对象
 * 4、执行代理对象方法时，先执行前置增强，然后是目标方法，最后是后置增强
 */
//其实在Spring中的AOP的动态代理实现的一个织入器也是叫做ProxyFactory 
public class ProxyFactory {
    private Object targetObject;//目标对象
    private BeforeAdvice beforeAdvice;//前值增强
    private AfterAdvice afterAdvice;//后置增强

    /**
     * 用来生成代理对象
     * @return
     */
    public Object creatProxy() {
        /**
         * 给出三个参数
         */
        ClassLoader classLoader = this.getClass().getClassLoader();
        //获取当前类型所实现的所有接口类型
        Class[] interfaces = targetObject.getClass().getInterfaces();

        InvocationHandler invocationHandler = new InvocationHandler() {
            @Override
            public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
                /**
                 * 在调用代理对象的方法时，会执行这里的内容
                 */
                if(beforeAdvice != null) {
                    beforeAdvice.before();
                }
                Object result = method.invoke(targetObject, args);//调用目标对象的目标方法
                //执行后续增强
                afterAdvice.after();

                //返回目标对象的返回值
                return result;
            }
        };
        /**
         * 2、得到代理对象
         */
        Object proxyObject = Proxy.newProxyInstance(classLoader, interfaces, invocationHandler);
        return proxyObject;

    }
//get和set方法略
}

```

```java
package demo3;

import org.junit.Test;

/**
 * Created by Yifan Jia on 2018/6/5.
 */
public class Demo3 {
    @Test
    public void tset1() {

        ProxyFactory proxyFactory = new ProxyFactory();//创建工厂
        proxyFactory.setTargetObject(new ManWaiter());//设置目标对象
        //设置前置增强
        proxyFactory.setBeforeAdvice(new BeforeAdvice() {
            @Override
            public void before() {
                System.out.println("客户你好");
            }
        });
        //设置后置增强
        proxyFactory.setAfterAdvice(new AfterAdvice() {
            @Override
            public void after() {
                System.out.println("客户再见");
            }
        });
        Waiter waiter = (Waiter) proxyFactory.creatProxy();
        waiter.server();

    }
}
```

使用静态代理的两种方式, jdk和cglib,前者是实现接口类,后者是继承重写方法.

> 让我们来假设一下, 从前有一个叫爪哇的小县城, 在一个月黑风高的晚上, 这个县城中发生了命案. 作案的凶手十分狡猾, 现场没有留下什么有价值的线索. 不过万幸的是, 刚从隔壁回来的老王恰好在这时候无意中发现了凶手行凶的过程, 但是由于天色已晚, 加上凶手蒙着面, 老王并没有看清凶手的面目, 只知道凶手是个男性, 身高约七尺五寸. 爪哇县的县令根据老王的描述, 对守门的士兵下命令说: 凡是发现有身高七尺五寸的男性, 都要抓过来审问. 士兵当然不敢违背县令的命令, 只好把进出城的所有符合条件的人都抓了起来.
>
> 来让我们看一下上面的一个小故事和 AOP 到底有什么对应关系.
>  首先我们知道, 在 Spring AOP 中 `Joint point` 指代的是所有方法的执行点, 而 point cut 是一个描述信息, 它修饰的是 `Joint point`, 通过 point cut, 我们就可以确定哪些 `Joint point` 可以被织入 `Advice`. 对应到我们在上面举的例子, 我们可以做一个简单的类比, **`Joint point` 就相当于 爪哇的小县城里的百姓**,**`pointcut` 就相当于 老王所做的指控, 即凶手是个男性, 身高约七尺五寸**, **而 `Advice` 则是施加在符合老王所描述的嫌疑人的动作: 抓过来审问**.

### mvc[加载](https://mp.weixin.qq.com/s/wW1F9SNLhYIlAsQ0lvGYAg)

 test

## [redis](https://mp.weixin.qq.com/s/8G_1E5yWKhZ9gjzzA8_-qw)

### [数据类型](https://mp.weixin.qq.com/s/GLqZf-0sLQ7nnJ8Xb9oVZQ)

- 基本的五种数据类型

> String，List，Hash，Set，Sorted Set
>
> String: set mset get mget del append  incr incrby decr decrby
>
> Hash: hset hmset hget hgetall hdel hlen hkeys hvals hincrby hdcrby
>
> List: lpush rpush lrange llen lindex lpop rpop
>
> Set: sadd smembers srem scard sismember
>
> sorted_set: zadd zrange zrevrange zrem zcard zcount
>
> 通用: exists del type expire ttl persist keys

- 高级的三中数据结构

> bitmap、GEO、HyperLogLog

- redis的持久化

> - rdb-将当前**数据状态**进行保存，**快照**形式，存储数据结果，存储格式简单，关注点在**数据**(方法是save和bgsave, save会堵塞线程,一般都使用bgsave)
> - aof-将数据的**操作过程**进行保存，**日志**形式，存储操作过程，存储格式复杂，关注点在数据的操作**过程**(config里面开启, 三种模式always和everysec和on,推荐everysec)

### [场景处理](https://mp.weixin.qq.com/s/M9ImkchlYfB5yc7chJs0uQ)

- 缓存预热

> #### 问题排查
>
> - 请求数量较高
> - 主从之间数据吞吐量较大，数据同步操作频度较高
>
> #### 解决方案
>
> - 前置准备工作：
>   - 日常例行统计数据访问记录，统计访问频度较高的热点数据
>   - 利用 LRU 数据删除策略，构建数据留存队列 例如：storm 与 kafka 配合
> - 准备工作：
>   - 将统计结果中的数据分类，根据级别，redis 优先加载级别较高的热点数据
>   - 利用分布式多服务器同时进行数据读取，提速数据加载过程
>   - 热点数据主从同时预热
> - 实施：
>   - 使用脚本程序固定触发数据预热过程
>   - 如果条件允许，使用了 CDN（内容分发网络），效果会更好
>
> #### 总结
>
> 缓存预热就是系统启动前，提前将相关的缓存数据直接加载到缓存系统。避免在用户请求的时候，先查询数据库，然后再将数据缓存的问题！用户直接查询事先被预热的缓存数据！

- 缓存雪崩

> #### 数据库服务器崩溃（1）
>
> 1. 系统平稳运行过程中，忽然数据库连接量激增
> 2. 应用服务器无法及时处理请求
> 3. 大量 408，500 错误页面出现
> 4. 客户反复刷新页面获取数据
> 5. 数据库崩溃
> 6. 应用服务器崩溃
> 7. 重启应用服务器无效
> 8. Redis 服务器崩溃
> 9. Redis 集群崩溃
> 10. 重启数据库后再次被瞬间流量放倒
>
> #### 问题排查
>
> 1. 在一个**较短**的时间内，缓存中较多的 key **集中过期**
> 2. 此周期内请求访问过期的数据，redis 未命中，redis 向数据库获取数据
> 3. 数据库同时接收到大量的请求无法及时处理
> 4. Redis 大量请求被积压，开始出现超时现象
> 5. 数据库流量激增，数据库崩溃
> 6. 重启后仍然面对缓存中无数据可用
> 7. Redis 服务器资源被严重占用，Redis 服务器崩溃
> 8. Redis 集群呈现崩塌，集群瓦解
> 9. 应用服务器无法及时得到数据响应请求，来自客户端的请求数量越来越多，应用服务器崩溃
> 10. 应用服务器，redis，数据库全部重启，效果不理想
>
> #### 问题分析
>
> - 短时间范围内
> - 大量 key 集中过期
>
> #### 解决方案（道）
>
> 1. 更多的页面静态化处理
> 2. 构建**多级缓存架构** Nginx 缓存 + redis 缓存 + ehcache 缓存
> 3. 检测 Mysql 严重耗时业务进行优化 对数据库的瓶颈排查：例如超时查询、耗时较高事务等
> 4. 灾难预警机制 监控 redis 服务器性能指标
>    - CPU 占用、CPU 使用率
>    - 内存容量
>    - 查询平均响应时间
>    - 线程数
> 5. 限流、降级 短时间范围内牺牲一些客户体验，限制一部分请求访问，降低应用服务器压力，待业务低速运转后再逐步放开访问
>
> 解决方案（术）
>
> 1. LRU 与 LFU 切换
> 2. 数据有效期策略调整
>    - 根据业务数据有效期进行**分类错峰**，A 类 90 分钟，B 类 80 分钟，C 类 70 分钟
>    - 过期时间使用固定时间 + 随机值的形式，**稀释**集中到期的 key 的数量
> 3. **超热**数据使用永久 key
> 4. 定期维护（自动 + 人工） 对即将过期数据做访问量分析，确认是否延时，配合访问量统计，做热点数据的延时
> 5. 加锁 **慎用！**
>
> #### 总结
>
> 缓存雪崩就是**瞬间过期数据量太大**，导致对数据库服务器造成压力。如能够**有效避免过期时间集中**，可以有效解决雪崩现象的出现 （约 40%），配合其他策略一起使用，并监控服务器的运行数据，根据运行记录做快速调整。

- 缓存击穿

> #### 数据库服务器崩溃（2）
>
> 1. 系统平稳运行过程中
> 2. 数据库连接量**瞬间激增**
> 3. Redis 服务器无大量 key 过期
> 4. Redis 内存平稳，无波动
> 5. Redis 服务器 CPU 正常
> 6. **数据库崩溃**
>
> #### 问题排查
>
> 1. Redis 中**某个 key 过期，该 key 访问量巨大**
> 2. 多个数据请求从服务器直接压到 Redis 后，均未命中
> 3. Redis 在短时间内发起了大量对数据库中同一数据的访问
>
> #### 问题分析
>
> - 单个 key 高热数据
> - key 过期
>
> #### 解决方案（术）
>
> 1. 预先设定
>
>    以电商为例，每个商家根据店铺等级，指定若干款主打商品，在购物节期间，**加大**此类信息 key 的**过期时长**
>
>    注意：购物节不仅仅指当天，以及后续若干天，访问峰值呈现逐渐降低的趋势
>
> 2. 现场调整
>
>    - 监控访问量，对自然流量激增的数据延长过期时间或设置为永久性 key
>
> 3. 后台刷新数据
>
>    - 启动定时任务，高峰期来临之前，刷新数据有效期，确保不丢失
>
> 4. 二级缓存
>
>    - 设置不同的失效时间，保障不会被同时淘汰就行
>
> 5. 加锁 分布式锁，防止被击穿，但是要注意也是性能瓶颈，**慎重！**
>
> #### 总结
>
> 缓存击穿就是**单个高热数据过期的瞬间**，数据访问量较大，未命中 redis 后，发起了大量对同一数据的数据库问，导致对数据库服务器造成压力。应对策略应该在业务数据分析与预防方面进行，配合运行监控测试与即时调整策略，毕竟单个 key 的过期监控难度较高，配合雪崩处理策略即可.

- 缓存穿透

> #### 恶意请求
>
> 我们的数据库中的主键都是从 0 开始的，即使我们将数据库中的所有数据都放到了缓存中。当有人用 id=-1 来发生**恶意请求**时，**因为 redis 中没有这个数据，就会直接访问数据库，这就称谓缓存穿透**, 
>
> #### 解决办法
>
> - 在程序中进行数据的合法性检验，如果不合法直接返回

## [mysql](https://mp.weixin.qq.com/s/mXTLt53s5iv0YNPOq4Y6uQ)

![img](https://upload-images.jianshu.io/upload_images/4476195-75305e1ba5c5dea9.png?imageMogr2/auto-orient/strip|imageView2/2/w/1104/format/webp)

### [ACID](https://mp.weixin.qq.com/s/-zRaWJNFa2_qKFfjZcWHqw)

### [索引](https://mp.weixin.qq.com/s/fUPESYvyno3SNKC7vxeDBA)

### [事务隔离级别](https://mp.weixin.qq.com/s/ToSkqwvKGCXSwyfglEV2FQ)

