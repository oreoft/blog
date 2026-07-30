---
layout: post
title: 一次 SQS 消费者静默退出的排查：问题最后竟然出在日志里
excerpt: Web 服务和消息生产都正常，唯独消费者处理一次业务异常后悄悄退出，最后发现真正杀死 Task 的不是业务代码，而是一行错误日志
category: middleware
keywords: python, sqs, loguru, asyncio, debugging
lang: zh
---

## 前言

前段时间遇到一个很诡异的问题：一个异步结算任务明明已经成功发送到了 SQS，但是迟迟没有被消费。刚开始我以为只是消息有点延迟，结果去看了一下队列，发现里面已经积压了几十条消息，而且没有一条处于正在处理的状态。

更奇怪的是，FastAPI 服务本身完全正常，健康检查是好的，接口也一直有人调用，负责发送消息的 SNS 日志也在不断输出。也就是说，**生产者还活着，Web 服务也活着，只有消费者悄悄没了。**

这个 SQS 消费者不是一个独立进程，而是 FastAPI 启动时创建的一个后台 asyncio Task。重启服务以后，积压消息又会继续被消费，看起来就像某一次处理把 poller 搞死了。但是日志里没有进程崩溃，也没有明显的未捕获异常，整个事情非常奇怪。

这次排查过程走了不少弯路。中间怀疑过 SQS 网络请求卡死、数据库 session 回滚、线程池阻塞，甚至怀疑过 Python 的 `for` 循环异常边界。最后不断做对照实验，才发现真正杀死消费者的，居然不是最开始的业务异常，而是**记录这个异常的那一行日志**。

## 先确认消息到底去了哪里

最开始发现问题，是因为有一条异步结算记录一直停留在“业务已经完成，但是异步结果还没写回”的中间状态。

正常流程大概是：

```text
用户请求
  ↓
业务状态落库
  ↓
发送异步结算事件
  ↓
SQS 消费者拉取消息
  ↓
执行结算并写回结果
```

这条数据说明前半段完成了，但后半段没有走完。第一反应自然是：是不是本地测试时把 MQ 开关关掉了，结果开发环境也没有打开？

但看完配置和生产者日志以后，这个方向很快就排除了。消息发送日志很完整，SNS 返回了消息 ID，说明消息确实发布成功。再去看 SQS，队列里存在大量可见消息，却没有正在被消费者处理的消息。

接着把同一个容器的日志按时间串起来，出现了一个很关键的现象：

- HTTP 请求一直正常；
- 健康检查一直正常；
- SNS 在这段时间内持续发布事件；
- SQS poller 在处理一次失败消息后，再也没有打印过“收到消息”；
- 直到服务下一次重启，poller 才重新打印启动日志。

这就基本可以确定了：**不是整个服务挂了，也不是消息没发出去，而是进程里的 SQS poller Task 单独没了。**

## 第一个怀疑：是不是异常没有被 catch 住

当时最后一条消费者日志，是一个类似“结算记录不存在”的业务异常。于是第一反应是检查消费者的异常处理。

脱敏后的结构大概如下：

```python
async def run_poller():
    while not stop_event.is_set():
        try:
            messages = await receive_messages()
        except Exception as exc:
            logger.error("Receive message failed: {}", exc)
            continue

        for message in messages:
            try:
                await process_message(message)
            except Exception as exc:
                logger.error(
                    f"Unexpected error processing message: {exc}",
                    exc_info=True,
                )
```

一开始我怀疑 `for message in messages` 外面还缺少一层 `try/except`。如果单条消息处理之外的某个地方抛异常，就可能直接冲出整个 `while` 循环。

但仔细一想，这个解释站不住脚。每条消息本身已经有 `try/except`，两次循环之间只是 Python 对 list 的普通遍历，没有业务逻辑，也没有 I/O，不能为了“多 catch 一层”就把锅甩给循环。

而且失败消息前面已经打印出了完整的业务异常堆栈，说明原始异常确实被 `_process_message()` 里面的异常处理捕获了。真正的问题应该发生在它被捕获以后。

这个方向只能先放下。

## 第二个怀疑：是不是 SQS 请求卡住了

失败路径和成功路径有一个区别：成功后会删除消息，失败后为了重试，会调用 `change_message_visibility` 修改消息的可见时间。

这些 boto3 调用本身是同步的，所以代码通过 `run_in_executor()` 把它们扔到了线程池里：

```python
await loop.run_in_executor(
    None,
    change_message_visibility,
    receipt_handle,
    retry_delay,
)
```

于是第二个猜测来了：会不会是失败以后调用 `change_message_visibility`，底层网络连接正好卡住，导致 poller 一直 await 在这里？

这个解释一度看起来非常合理：

- 只有失败路径才会调用它；
- poller 自己卡住不会影响 FastAPI 的其他 Task；
- HTTP 服务继续正常，和现象完全对得上；
- 重启后连接重建，消费者又恢复了。

甚至还考虑过给 boto3 配置 `connect_timeout`、`read_timeout`，再在外面加一层 `asyncio.wait_for()`。

但是这里一直缺少直接证据。`run_in_executor()` 的确不会卡住整个 event loop，但是“不会卡 event loop”和“不会卡当前 poller Task”是两回事。即便线程池里的函数永久不返回，这个 poller 还是会永远等在当前 `await` 上。

理论上说得通，但我们没有看到它真的停在这里。再继续靠猜，基本只是在不同的“合理故事”之间来回切换。

所以后面干脆不猜了，开始加追踪日志做可控复现。

## 不再猜了，开始做对照实验

我给消息消费链路的每个关键节点都加了编号日志：

```text
T1  捕获业务处理异常
T2  准备写入失败状态
T3  失败状态提交完成
T4  process_message 捕获异常
T5  计算重试间隔
T6  释放分布式锁
T7  锁释放完成
T8  进入失败后的重试分支
T9  准备修改消息可见性
T10 可见性修改完成
T11 准备重新抛出原异常
T12 原异常已经抛给 poller
T13 poller 最外层 catch 捕获异常
```

然后开始构造不同类型的失败消息。

### 普通 ValueError

先发一条没有注册 handler 的事件，让 dispatch 直接抛一个普通 `ValueError`。整条链路从 T1 走到了 T13，随后 poller 继续进入下一轮 `receive_message`，完全正常。

### 非法 UUID

再给任务传一个格式错误的 UUID，让 Python 标准库抛：

```text
ValueError: badly formed hexadecimal UUID string
```

结果依然正常。消息重试了几次，poller 每次都能完整走过 T1 到 T13，然后继续下一轮循环。

### 数据库上下文中抛错

接着构造一个更接近真实业务的场景：打开异步数据库 session，执行一次查询，让事务真正建立起来，然后在 session 上下文中抛异常。

这个测试主要是为了验证，会不会是 session 退出时的 rollback 或 close 导致失败链路卡住。结果还是正常，数据库上下文退出、失败状态提交、消息可见性修改、异常重新抛出，全都能走完。

到这里，网络卡死、数据库回滚和消费者异常结构本身都越来越不像根因了。

### 换成真实的业务异常

最后把异常换成了真实业务里那种带错误详情的异常，不过业务名字和数据这里全部换成通用示例：

```python
class SettlementConflictError(Exception):
    def __init__(self, message: str):
        detail = {
            "type": "settlement_conflict",
            "message": message,
            "retryable": True,
        }
        super().__init__(detail)
```

这一次，问题稳定复现了。

日志走完 T13，说明 poller 外层已经成功捕获了原始业务异常。但是 T13 后面本应紧接着出现的错误日志没有打印，下一轮 poller 心跳也没有出现。

与此同时，另一个独立的后台 Task 还在正常输出日志，HTTP 请求也正常。也就是说整个进程和 event loop 都没死，**唯独 SQS poller Task 在 T13 后面那一行代码上退出了。**

T13 后面没有 `await`，只有一行日志：

```python
logger.error(
    f"Unexpected error processing message: {exc}",
    exc_info=True,
)
```

排查范围终于从一整条 MQ、数据库和异步调用链，缩小到了一行日志。

## 问题最后停在了一行日志上

为了验证是不是日志本身的问题，我又做了几个小实验：

```python
print("before logger.error")

logger.error("static message")

logger.error(f"Unexpected error processing message: {exc}")

print("after logger.error")
```

把 `exc_info=True` 完全去掉以后，消费者可以正常继续下一轮循环。

这里还有一个很容易误导人的细节：一开始只是把它改成了 `exc_info=False`，结果消费者照样会挂。刚开始很容易认为“既然 False 也会挂，那就不是 `exc_info` 的问题”。

实际上，Loguru 根本不关心这个值是 `True` 还是 `False`。对它来说，关键是**你传了一个额外的关键字参数**。只要 `kwargs` 非空，它就会触发消息模板格式化。

真正的区别也终于解释通了：

| 异常 | `str(exc)` 的结果 | 是否复现 |
|---|---|---|
| 普通 `ValueError` | `badly formed hexadecimal UUID string` | 否 |
| 业务异常 | `{'type': 'settlement_conflict', ...}` | 是 |

两个异常都能被正常 catch，区别不在异常继承关系，也不在数据库上下文，而在于**它们转换成字符串以后，有没有花括号**。

## 真正的根因：Loguru 又格式化了一次

`exc_info=True` 是 Python 标准库 `logging` 的用法，作用是把当前异常的 traceback 一起输出：

```python
import logging

try:
    do_something()
except Exception:
    logging.getLogger(__name__).error(
        "Something failed",
        exc_info=True,
    )
```

但是项目里使用的是第三方日志库 Loguru。Loguru 打印当前异常应该使用：

```python
logger.exception("Something failed")
```

或者：

```python
logger.opt(exception=True).error("Something failed")
```

Loguru 的 `error()` 接口会把额外的位置参数和关键字参数当成消息模板的格式化参数。内部逻辑可以简化理解成：

```python
def error(message, *args, **kwargs):
    if args or kwargs:
        message = message.format(*args, **kwargs)
    write_log(message)
```

再回到出问题的代码：

```python
logger.error(
    f"Unexpected error processing message: {exc}",
    exc_info=True,
)
```

这里首先发生的是 f-string 拼接。业务异常的 `str(exc)` 是一个 Python dict 的字符串形式，所以传给 Loguru 的成品消息已经变成：

```text
Unexpected error processing message:
{'type': 'settlement_conflict', 'message': 'record not found', 'retryable': True}
```

注意，这不是 JSON，而是 Python `dict` 的字符串表示。它有单引号、`True`，最重要的是，它有一对花括号。

然后 Loguru 又看到了额外的 `exc_info=True`，于是对这条已经拼好的消息再执行一次：

```python
message.format(exc_info=True)
```

Python 的 `str.format()` 会把花括号当成占位符。于是异常详情里的 `{'type': ...}` 不再是一段普通文字，而被当成了一个需要替换的字段。参数里当然没有与它匹配的内容，最终又抛出一个新的 `KeyError`。

所以完整异常链其实是：

```text
结算任务抛出 SettlementConflictError
  ↓
业务异常被正常捕获，失败状态和重试时间也正常写入
  ↓
原异常重新抛给 poller 外层
  ↓
poller 外层 catch 再次捕获，准备记录错误日志
  ↓
Loguru 对包含花括号的成品消息执行 str.format()
  ↓
日志代码抛出新的 KeyError
  ↓
新异常逃出 while 循环，poller Task 结束
```

也就是说，**原始业务异常从头到尾都被正确处理了。真正没有被处理的是异常处理代码里产生的第二个异常。**

这也解释了为什么非法 UUID 不会复现。它的错误信息只是普通文本，没有花括号。即便 Loguru 多执行了一次 `.format(exc_info=True)`，字符串里没有任何占位符，最终还是原样返回，看起来一切正常。

这个 bug 最隐蔽的地方就在这里：同一行错误日志已经运行了很久，大部分异常都没问题，只有某一种异常的字符串恰好带花括号时，才会突然把消费者干掉。

## 为什么整个服务没挂，消费者却静默退出了

这里还涉及一个很容易混淆的 asyncio 概念：**协程函数不等于独立 Task。**

消费者启动时大概是：

```python
poller_task = asyncio.create_task(run_poller())
```

这时创建了一个独立的 poller Task。但是后面：

```python
await process_message(message)
await dispatch(event)
await handle_settlement(payload)
```

这些 `await` 并不会为每一层自动创建新的 Task。它们仍然在最开始那个 `poller_task` 里连续执行，只是调用栈一层层向下。

所以当最外层错误日志抛出的 `KeyError` 冲出 `run_poller()`，结束的只是这个 poller Task。FastAPI 处理 HTTP 请求的 Task、健康检查、其他后台任务都还活着，整个容器自然不会退出。

从外面看就会出现一种非常迷惑的状态：

```text
容器：Running
健康检查：200
接口请求：正常
生产消息：正常
SQS 队列：持续积压
消费者：已经死了
```

那为什么连常见的：

```text
Task exception was never retrieved
```

都没有看到？

asyncio 通常会在一个带异常结束的 Task 没有被读取结果、并且 Task 对象被销毁时，通过 event loop 的异常处理器给出这条提示。但我们的 lifespan 代码一直持有 `poller_task` 的引用，准备在服务关闭时再统一 cancel 和 await。

Task 虽然已经结束，但对象一直没有被回收，因此这个兜底提示没有及时出现。服务不重启，它就可以长时间保持“Task 已经死了，但引用还活着”的状态。

这也是为什么这次故障看起来这么安静。

## 修复

直接修复其实很简单，把标准库 `logging` 的写法换成 Loguru 自己的 API：

```python
try:
    await process_message(message)
except Exception:
    logger.exception("Unexpected error processing message")
```

`logger.exception()` 会自动附带当前正在处理的 traceback，不需要再传 `exc_info=True`。

如果还想把异常对象作为消息的一部分，也可以使用 Loguru 自己的占位符：

```python
try:
    await process_message(message)
except Exception as exc:
    logger.exception(
        "Unexpected error processing message: {}",
        exc,
    )
```

这里模板字符串是我们自己控制的，只有一个明确的 `{}`。`exc` 作为参数填进去以后，它字符串里的花括号不会再被递归解析，所以是安全的。

定位以后，我又把整个项目扫描了一遍。因为这种误用不一定只出现在消费者里，只要同时满足下面两个条件，就可能踩坑：

1. 使用 Loguru，却传了标准库 `logging` 的 `exc_info=`；
2. 最终日志消息里出现了未转义的花括号。

所以修复不能只改事故现场的一行。更稳妥的做法是：

- 全仓搜索 Loguru 调用中的 `exc_info=`；
- `except` 块里统一改成 `logger.exception()`；
- 需要更细控制时使用 `logger.opt(exception=True)`；
- 真正使用标准库 `logging` 的地方不要误改，它本来就支持 `exc_info=True`。

同时还补了一个回归测试，核心不是测试某个具体业务错误，而是构造一个**字符串中带花括号的异常**，先让第一条消息失败，再确认消费者仍然能处理第二条消息：

```python
class BraceError(Exception):
    pass


async def test_poller_survives_brace_error():
    messages = [
        BraceError({"type": "conflict"}),
        "next-message",
    ]

    processed = await run_test_poller(messages)

    assert "next-message" in processed
```

这样以后即使有人又把标准库日志写法复制进来，测试也会直接把它拦住。

最后，长期运行的后台 Task 最好再加一层生命监控。比如给 Task 增加 done callback：

```python
def report_task_exit(task: asyncio.Task) -> None:
    if task.cancelled():
        return

    error = task.exception()
    if error is not None:
        logger.error("SQS poller exited unexpectedly: {}", error)


poller_task = asyncio.create_task(run_poller())
poller_task.add_done_callback(report_task_exit)
```

更完整一点，可以用 supervisor 在异常退出后报警或重启消费者。不过要注意，自动重启只能作为可用性兜底，不能代替对根因的修复。不然 Task 不断崩溃、不断拉起，只是把“静默死亡”变成“静默重启”。

## 后言

这次排查下来，最深的感受是：**一个解释听起来合理，和它有证据，是两回事。**

网络卡死、数据库 rollback、线程池阻塞，这些方向都能解释一部分现象，而且每个都很像那么回事。如果当时直接按某个猜测去加超时、加重试，可能消费者看起来暂时稳定了，但真正的问题还是埋在日志里，下一次遇到带花括号的异常照样会炸。

最后真正让问题收敛的，不是继续读一大堆代码，而是不断缩小变量：

- 普通异常有没有问题？
- 数据库上下文会不会改变结果？
- 同一条调用链换一种异常会怎样？
- 两种异常转成字符串以后到底差在哪里？
- poller 最后一条成功执行的代码是哪一行？

一层层对照以后，整个问题从“SQS 消费者为什么会挂”缩小成“为什么这一行 Loguru 会抛 `KeyError`”，难度一下就降下来了。

另外以前总觉得日志只是旁路代码，打失败了最多就是少一条日志，不应该影响业务。这次算是重新认识了：**日志也在真实执行路径里，只要它是同步调用，就完全有能力抛异常、改变控制流，甚至杀死一个长期运行的消费者。**

有时候真正危险的不是原始异常，而是我们在处理异常时，又制造了一个新的异常。
