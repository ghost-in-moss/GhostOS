# ChatBot

基于 LLM 实现的对话机器人, 由于非常简单, 是 `GhostOS` 开发时的基线测试对象. 
它是 [Ghost](docs/zh-cn/usages/ghost.md) 一个最简单的实现. 

要创建属于自己的对话机器人, 可以参考文件 
[ghostos/demo/agents/jojo.py](https://github.com/ghost-in-moss/GhostOS/ghostos/demo/agents/jojo.py):

```python
from ghostos.ghosts.chatbot import Chatbot

# the __ghost__ magic attr define a ghost instance
# so the script `ghostos web` or `ghostos console` can detect it 
# and run agent application with this ghost.
__ghost__ = Chatbot(
    name="jojo",
    description="a chatbot for baseline test",
    persona="you are an LLM-driven cute girl, named jojo",
    instruction="remember talk to user with user's language."
)
```

想要定义自己的 chatbot, 只需要创建一个类似的 python 文件, 然后运行 `ghostos web` 命令调用它. 

> streamlit 生成的界面可以直接通过 `settings` 选项修改 ghost 的配置.
> 修改结果会保存到一个本地文件 `.ghosts.yml` 中, 这样 `ghostos web` 启动时优先读取 `.ghosts.yml` 中的配置. 

通过对话生成 chatbot 的 meta-agent 正在测试中, 未来几个版本会放出. 

`GhostOS` 核心的 Agent 设计是全代码交互的 [MossAgent](./moss_agent.md), 详见文档. 