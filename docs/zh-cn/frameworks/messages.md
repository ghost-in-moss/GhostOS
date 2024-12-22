# Messages

`GhostOS` 的设计目标之一, 是实现服务端全异步的智能体集群.
因此历史消息的传输和存取不能仅仅在客户端, 还需要在服务端.

为了解决消息协议的流式传输, 模型兼容, 存储与读取等问题; `GhostOS` 设计了自己的消息容器. 
详见 [ghostos.core.messages](https://github.com/ghost-in-moss/GhostOS/ghostos/core/messages/message.py)

目前没有精力介绍所有的细节, 重点介绍几个关键概念: 


## Variable Message

`GhostOS` 的 agent 使用代码驱动, 所以它可以把各种运行时的变量通过 `VariableMessage` 形式传输, 包括: 

1. 传入给端侧, 比如 streamlit
2. 传输给其它的 Agent

在历史记录中, LLM 可以看到变量的 `vid` 参数, 
使用 [ghostos/contracts/variables](https://github.com/ghost-in-moss/GhostOS/ghostos/contracts/variables.py) 库可以获取对应的变量. 
从而可以实现基于变量的交互. 

举例: 

1. Agent 将自己的变量, 传输给另一个 Agent.
2. Agent 将某个数据结构的变量发送给端, 端侧自行渲染.
3. 端侧可以将变量以消息方式发送, 而 Agent 可以在代码中获取变量数据结构, 并操作它. 
4. Agent 可以操作历史上下文中看到的变量. 

## Audio & Image Message

`GhostOS` 历史消息中的图片和音频都会使用中心化的存储, 消息 id 就是 图片 & 音频 的存储 id.
详见 [ghostos/contracts/assets](https://github.com/ghost-in-moss/GhostOS/ghostos/contracts/assets.py).

预期未来 Audio 和 Image 也支持 `变量类型消息`, 从而大模型可以用代码来操作它们. 

比如一个没有识图能力的大模型, 通过代码调用另一个可识图的模型来帮助自己阅读图片. 

