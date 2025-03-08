# Entity Meta

基于代码驱动的 AI Agent 需要在运行过程中将各种数据进行存储, 同时能在后续运行中还原变量. 
考虑到 `分布式系统` 或是 `可中断 Agent`, 这些数据需要有长期存储的方案. 

`GhostOS` 以 `pickle` 和 `pydantic` 为基础, 
实现了 [EntityMeta](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/entity.py).

它旨在: 
1. 把绝大部分可存取的 python 数据结构进行序列化和反序列化
2. 并提供通用的容器和 API 来操作数据
3. 尽可能保证数据的可读性. 

更多技术细节详见代码. 

