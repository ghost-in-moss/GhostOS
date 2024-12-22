# EventBus

`GhostOS` 通过 [EventBus](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/core/runtime/events.py) 类来管理 Agent 之间,
Agent 和外部世界, Agent 自身的事件通讯.

基于事件总线, 我们可以实现一个全异步的 Agent. 以耗时较长的网络叫车为例子:

1. 用户和主 Agent 对话, 要求 Agent 叫车.
2. Agent 调用拥有叫车能力的子 Agent, 让它去执行任务.
3. Agent 继续和用户对话.
4. Agent 可以随时询问子 Agent 任务执行情况.
5. 子 Agent 打到车后, 通过 Event 通知主 Agent.

事件总线维持所有 Agent 的 Event Loop, 从而实现了全异步的通讯.

除了 Agent 之间的通讯外, 外部系统和 Agent 的通讯也需要通过 EventBus. 不过在 `ghostos.abcd.Conversation` 抽象中内置了相关接口.
外部系统的通讯可以包括:

* 环境中发生的事件
* 定时任务
* 接口的异步回调

# Event 对象的设计

GhostOS
中的事件对象定义在 [ghostos.core.runtime.events.Event](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/core/runtime/events.py).
相关 API 详见代码.

# EventBus 的注册

作为基础类, EventBus 在 `ghostos.bootstrap.app_container` 中注册.
只需要变更 EventBus 注册的 Provider, 就可以修改它的实现. 详见 Container 相关章节.

# EventBus 的实现

`EventBus` 可以有各种技术实现, 包括基于文件的, 基于关系型数据库的, 基于 Redis 等 KV 存储的. 从而实现分布式系统的事件总线.

由于 `GhostOS` 没有开发人力, 目前的实现是基于内存的 dict.
详见 [MemEventBusImpl](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/framework/eventbuses/memimpl.py).
这意味着关闭运行中的程序, 就会导致事件丢失.

# EventBus 的配置化

未来希望将 EventBus 的系统默认实现变成可配置的, 用户可以通过配置项选择 `file`, `redis`, `mysql` 等几种开箱自带方案. 