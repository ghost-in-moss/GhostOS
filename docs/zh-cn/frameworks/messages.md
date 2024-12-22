# Messages

`GhostOS` 的设计目标之一, 是实现服务端全异步的智能体集群.
因此历史消息的传输和存取不能仅仅在客户端, 还需要在服务端.

为了解决消息协议的流式传输, 模型兼容, 存储与读取等问题; `GhostOS` 设计了自己的消息容器. 
详见 [ghostos.core.messages](../../../ghostos/core/messages/message.py)

目前没有精力介绍所有的细节, 重点介绍几个关键概念: 


## Variable Message


## Audio & Image Message

