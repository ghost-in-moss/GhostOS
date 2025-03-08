# Threads

`GhostOS` 为了实现全异步的 Multi-Agent, 需要自己管理所有 Agent 的上下文.

所以 `GhostOS` 实现了一个类似 [OpenAI Assistant](https://platform.openai.com/docs/api-reference/assistants) 的基建.

Agent 生成的历史消息, 会用 `GoThreadInfo` 结构存储和使用.

由于个人开发精力有限,
详细实现请看[ghostos.core.runtime.threads](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/core/runtime/threads.py) 