# Libraries

对于传统基于 `JSON Schema Function Call` 实现的 Agent 而言, 它的交互对象是 `Tool`.
而 `GhostOS` 以图灵完备的代码提供给 Agent, 所以 Agent 的交互对象是 `Library`. 

这里的 `libraries` 不是给开发者用的, 而是给大模型用的. 

让 LLM 使用 Library 有三个步骤: 

1. 定义和实现一个 Library. 
2. 将 Library 抽象和实现注册到 IoC Container. 
3. 将 Library 绑定到 Moss 类上.

## Code As Prompt

这其中一个核心的概念是 `Code As Prompt`, 写代码的同时就在定义 Prompt. 我们以多任务调度为例: 

```python
class Subtasks(Prompter, ABC):
    """
    library that can handle async subtasks by other ghost instance.
    """
    MessageKind = Union[str, Message, Any]
    """message kind shall be string or serializable object"""

    @abstractmethod
    def cancel(self, name: str, reason: str = "") -> None:
        """
        cancel an exists subtask
        :param name: name of the task
        :param reason: the reason to cancel it
        :return:
        """
        pass

    @abstractmethod
    def send(
            self,
            name: str,
            *messages: MessageKind,
            ctx: Optional[Ghost.ContextType] = None,
    ) -> None:
        """
        send message to an existing subtask
        :param name: name of the subtask
        :param messages: the messages to the subtask
        :param ctx: if given, update the ghost context of the task
        :return:
        """
        pass

    @abstractmethod
    def create(
            self,
            ghost: Ghost,
            instruction: str = "",
            ctx: Optional[Ghost.ContextType] = None,
            task_name: Optional[str] = None,
            task_description: Optional[str] = None,
    ) -> None:
        """
        create subtask from a ghost instance
        :param ghost: the ghost instance that handle the task
        :param instruction: instruction to the ghost
        :param ctx: the context that the ghost instance needed
        :param task_name: if not given, use the ghost's name as the task name
        :param task_description: if not given, use the ghost's description as the task description
        """
        pass
```

将它绑定到 Agent 可以看到的 moss 文件上: 

```python
from ghostos.abcd import Subtasks
from ghostos.core.moss import Moss as Parent

class Moss(Parent):
    
    subtasks: Subtasks
    """manager your multi-agent tasks"""
```

* 类的源码会自动反射到 Prompt, 让大模型看到. 
* 这个库的实现会自动注入到 `Moss` 实例上, 大模型可以用生成的代码调用它.

更具体的用法, 请看 [MossAgent](/zh-cn/usages/moss_agent.md).

我们预期基于 [MOSS Protocol](/zh-cn/concepts/moss_protocol.md) 类似的行业标准化协议, 未来大模型使用的工具, 会单纯以代码仓库的形式开发和分享. 


## Developing Libraries

`GhostOS` 开箱自带的 libraries 还在开发和测试中. 
这些工具预期都会放入 [ghostos/libraries]((https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/libraries))