# Moss Agent

`MossAgent` 是 `GhostOS` 项目最基本的 Agent 单元. 它使用 [MOSS Protocol](/zh-cn/concepts/moss_protocol.md) 提供代码交互界面,
让 LLM 可以生成代码来驱动自己的行为.

## Simplest Example

创建文件 `foo.py`:

```python

def plus(a: int, b: int) -> int:
    return a + b
```

执行 `ghostos web foo.py`, 要求 agent 调用 `plus` 方法.

## Run Agent

运行命令 `ghostos web [python_modulename_or_filename]` 可以将 python 文件直接变成 Agent, 并用 streamlit 运行.

例如:

```bash
ghostos web ghostos/demo/agents/jojo.py
# or 
ghostos web ghostos.demo.agents.jojo
```

命令执行时, 如果目标文件不存在 `__ghost__` 属性, 则会反射目标文件,
生成 [MossAgent](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/ghosts/moss_agent/agent.py) 实例.
这个 Agent 可以调用目标文件提供的函数和类, 执行你用自然语言提出的任务.

源码如下:

```python
class MossAgent(ModelEntity, Agent):
    """
    Basic Agent that turn a python module into a conversational agent.
    """

    """ subclass of MossAgent could have a GoalType, default is None"""

    moss_module: str = Field(description="Moss module name for the agent")
    persona: str = Field(description="Persona for the agent, if not given, use global persona")
    instructions: str = Field(description="The instruction that the agent should follow")

    # optional configs
    name: str = Field(default="", description="name of the agent")
    description: str = Field(default="", description="description of the agent")
    code: Optional[str] = Field(default=None, description="code override the module")
    compile_module: Optional[str] = Field(None, description="Compile module name for the agent")
    llm_api: str = Field(default="", description="name of the llm api, if none, use default one")
    truncate_at_turns: int = Field(default=40, description="when history turns reach the point, truncate")
    truncate_to_turns: int = Field(default=20, description="when truncate the history, left turns")
```

你也可以在目标文件里手动定义一个 `__ghost__` 对象, 方便定义详细的 instructions:

```python

# the python module codes
...

# <moss-hide>
# add and agent definition manually at the tail of the file.
from ghostos.ghosts.moss_agent import MossAgent

__ghost__ = MossAgent(
    moss_module=__name__,
    name="agent name",
    description="agent desc",
    persona="persona",
    instruction="system instructions",
    # use llms model defined at app/configs/llms_conf.yml
    llm_api="moonshot-v1-128k",
)

# </moss-hide>
```

> 通常一个 python 文件不做改动也是可以直接作为 agent 启动的.
> 比如单元测试文件.

## Code As Prompt

MossAgent 会自动将目标 Python 模块反射成 Prompt, 提供给大模型.
想要看到详细的 prompt, 可以用 `ghostos web` 生成界面上的 `instructions` 按钮查看它的 system instruction.

默认的反射原理, 请看 [MOSS Protocol](/zh-cn/concepts/moss_protocol.md). 简单来说:

1. 引用的函数会自动反射出函数名 + doc
2. 抽象类反射出源代码

大模型会根据 instruction, 调用名为 `moss` 的工具, 生成代码.
生成的代码会在 [Moss](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/moss/ghostos_moss/abcd.py) 编译的临时模块中执行.

源码请看 [MossAction](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/ghosts/moss_agent/agent.py#MossAction).

如果一部分源码不想让 LLM 看到, 可以使用`# <moss-hide>` 和 `# </moss-hide>` 标记:

```python

# <moss-hide>
...
# the code here is not visible to llm
# </moss-hide>
```

如果自动反射的结果不让人满意, 也可以通过魔术方法 `__moss_attr_prompts__` 手动定义:

```python
from foo import Foo


# <moss-hide>

def __moss_attr_prompts__():
    """
    :return: Iterable[Tuple[attr_name: str, attr_prompt: str]]
    """
    yield "Foo", ""  # if the prompt is empty, won't prompt it to llm
# </moss-hide>
```

[MOSS Protocol](/zh-cn/concepts/moss_protocol.md) 系统默认的魔术方法在
[lifecycle](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/moss/ghostos_moss/lifecycle.py).

## Magic lifecycle functions

`MossAgent` 使用各种文件内的魔术方法来定义其特殊的运行逻辑.
这种做法的好处第一是简化开发者使用; 第二则是对于 Meta-Agent 来说, 简化创建 Agent 时的工作量.

所有的生命周期方法可以查看以下三个文件:

- [for developer](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/ghosts/moss_agent/for_developer.py): 面向开发者的生命周期管理
    - `__moss_agent_providers__`
    - `__matrix_providers__`
    - `__moss_agent_creating__`
    - `__moss_agent_truncate__`: 按需压缩历史消息
    - `__moss_agent_parse_event__`: 事件拦截
    - `__moss_agent_injections__`: 手动依赖注入
    - `__moss_agent_on_[event_type]__`: 自定义事件处理
- [for meta ai](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/ghosts/moss_agent/for_meta_ai.py): 面向开发者和 AI
  的生命周期管理
    - `__moss_agent_artifact__`: 定义 agent 的输出
    - `__moss_agent_actions__`: 定义 moss 之外的工具
    - `__moss_agent_thought__`: 定义思维链
    - `__moss_agent_instruction__`: 定义 instruction 获取方法
    - `__moss_agent_persona__`: 定义 persona 获取方法
- [moss lifecycle](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/moss/ghostos_moss/lifecycle.py): Moss 库的生命周期方法.

复制这些方法到当前文件, 既可以生效自定义魔术方法.
所有这些魔术方法都是 `可选的`. 如果能用来解决问题, 则可以使用它们.

如果一切魔术方法都不够用, 那么最好的办法是自己实现 `Ghost` 和 `GhostDriver` 类,
详见 [concepts.py](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/abcd/concepts.py)

## Define Moss Class

通常 import 类和方法足以让 Agent 运行. 但有两种情况需要引入 `Moss` 类 (Model-oriented Operating System Simulator):

1. `Context Manage`: 希望定义在多轮对话中可以持续变更的变量
2. `Runtime Injection`: 通过 [IoC Container](/zh-cn/concepts/ioc_container.md) 进行依赖注入.

在目标文件中定义一个 Moss 类:

```python
from ghostos_moss import Moss as Parent


# 名为 Moss 的类是一个特殊的类. 
class Moss(Parent):
    ...
    pass
```

是否定义这个类, 都会在 MossAgent 运行时生成一个 `moss` 对象. 而 MossAgent 撰写的代码也是使用它, prompt 如下 (
会不断优化) :

```markdown
You are able to call the `moss` tool, generate code to fulfill your will.
the python code you generated, must include a `run` function, follow the pattern:

\```python
def run(moss: Moss):
    """
    :param moss: instance of the class `Moss`, the properties on it will be injected with runtime implementations.
    :return: Optional[Operator] 
             if return None, the outer system will perform default action, or observe the values you printed.
             Otherwise, the outer system will execute the operator. 
             You shall only return operator by the libraries provided on `moss`.
    """
\```
```

详见 [instructions](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/ghosts/moss_agent/instructions.py)

### Define Variables On Moss

Moss 类上挂载的 `str`, `float`, `int`, `bool`, `str` 和 `pydantic.BaseModel` 类型数据会自动保存,
因此 MossAgent 可以直接使用他们做变量.

注意这些变量类型必须保证可以序列化. 举例:

```python
from ghostos_moss import Moss as Parent
from pydantic import BaseModel, Field


class YourVariables(BaseModel):
    variables: dict = Field(default_factory=dict, description="you can manage your variables here")


# 名为 Moss 的类是一个特殊的类. 
class Moss(Parent):
    vars: YourVariables = YourVariables()
```

进一步的,
如果挂载的数据对象实现了 [ghostos_common.prompter.Prompter](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/prompter.py),
MossAgent 会自动在 system instruction 中生成 prompt 提供给大模型.

相关逻辑详见 `ghostos.ghosts.moss_agent.instructions.get_moss_context_prompter` 函数.

### Runtime Injection

Moss 类上挂载的 `abstract class` 会自动从 [IoC Container](/zh-cn/concepts/ioc_container.md) 进行依赖注入.
为这些抽象类提供实现有三种方法:

- 定义时传入实例:

```python
from ghostos_moss import Moss as Parent


class Foo:
    ...
    pass


# 名为 Moss 的类是一个特殊的类. 
class Moss(Parent):
    foo: Foo = Foo()
```

- 通过魔术方法 `__moss_agent_injections__`, 手动定义注入的实例

```python
from ghostos_moss import Moss as Parent
from foo import Foo


class Moss(Parent):
    foo: Foo


# <moss-hide>
# the code in moss-hide is invisible to llm

def __moss_agent_injections__(agent, session) -> Dict[str, Any]:
    """
    manually define some of the injections to the Moss Class.
    if a property of Moss is not injected here, the session container will inject it by typehint.
    """
    from foo.impl import FooImpl
    return {
        "foo": FooImpl(...)
    }
# </moss-hide>
```

第三种方法是在 [IoC Container](/zh-cn/concepts/ioc_container.md) 中注册依赖实现.
`Moss` 在实例化时会根据类型分析, 自动做依赖注入.
有以下几个方法进行依赖注册.

## Register dependencies

`GhostOS` 在运行时通过可继承的 `IoC Container Tree` 来隔离不同级别的依赖. 系统默认存在的容器有以下几个级别:

- [App Root Container](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/bootstrap.py) : 进程唯一容器
- `GhostOS.container` : 进程唯一容器, 基本和 App Root Container 相等.
- `Shell.container` : 对于同一个进程内, 所有平行运行的 Ghost 共享的容器. 通常用来启动和躯体相关的单例.
- `Conversation.container`: 对于单个 Ghost 拥有的依赖.
- `MossRuntime.container`: 每次 MossRuntime 被编译时, 生成的临时容器. 用来注册 `MossRuntime` 自身.

在 `MossAgent` 运行时进行依赖注入的是 `MossRuntime.container`, 因此它会继承每一层父容器的注册依赖, 也可以重写它们.

部分 `GhostOS` 系统提供的依赖如下:

- [LoggerItf](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/contracts/logger.py): 日志
- [Configs](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/contracts/configs.py): 配置文件
- [Workspace](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/contracts/workspace.py): 工作区
- [Variables](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/contracts/variables.py): 持久化变量存储
- [LLMs](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/core/llms/llms.py): 大模型
- [Assets](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/contracts/assets.py): 图片和音频
- [GhostOS](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/abcd/concepts.py): GhostOS 自身
- [Shell](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/abcd/concepts.py): 运行时生成的 Shell
- [Conversation](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/abcd/concepts.py): 运行时生成的 conversation
- [Session](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/abcd/concepts.py): 运行时生成的 Session, 管理主要的 API
- [Scope](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/abcd/concepts.py): 当前对话的座标.
- [Ghost](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/abcd/concepts.py): 当前 Agent 自身
- [MossCompiler](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/moss/ghostos_moss/abcd.py): moss 编译器
- [Tasks](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/core/runtime/tasks.py): 任务存储
- [Threads](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/core/runtime/threads.py): 历史消息存储
- [EventBus](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/core/runtime/events.py): 事件总线.

更多系统级绑定可调用 `Container.contracts(recursively=True)` 来调试.

### MossAgent dependencies

最简单的方法, 是在 Python 文件里直接用魔术方法定义依赖:

```python

# <moss-hide>

def __moss_agent_providers__(agent: A) -> Iterable[Provider]:
    """
    return conversation level providers that specially required by the Agent.
    the conversation container will automatically register the providers and run them.

    :param agent: the moss agent instance.
    :return: providers that register to the session container.
    """
    return []

# </moss-hide>
```

这些依赖会在 `Conversation` 创建时进行注册.

### Register root dependencies

修改全局容器, 或者创建自己的容器, 都可以在过程中注册服务:

```python
from ghostos.bootstrap import reset, make_app_container

# 定义新的全局容器
new_root_container = make_app_container(...)

# 重置 ghostos.bootstrap.app_container
reset(new_root_container)
```

这样可以注册进程级别的依赖, 对所有容器生效.

### Register Shell dependencies

在 Shell 启动时可以注册它的依赖. 一个进程可能会反复开启多个 Shell, 因此 Shell 有单独的隔离级别.

最简单的是在生命周期启动 shell 时注册:

```python
from ghostos.bootstrap import get_ghostos

ghostos = get_ghostos()

# register shell level providers at when shell is creating
shell = ghostos.create_shell("shell name", providers=[...])
```

对于使用 `ghostos web` 或 `ghostos console` 启动的 python 文件, 也可以简单注册在文件的魔术方法内:

```python
# <moss-hide>

def __matrix_providers__() -> Iterable[Provider]:
    """
    return shell level providers that specially required by the Agent.
    if the shell is running by `ghostos web` or `ghostos console`,
    the script will detect the __matrix_providers__ attribute and register them into shell level container.

    You can consider the Shell is the body of an agent.
    So shell level providers usually register the body parts singletons, bootstrap them and register shutdown functions.
    """
    return []
# </moss-hide>
```

这个方法里定义的 providers, 会在运行 `ghostos web` 时自动加载到 shell 中.

## Register Conversation dependencies

通常 `__moss_agent_providers__` 魔术方法可以完成 Conversation 依赖的注册.
但如果还需要手动的话, 则应该在创建 Conversation 时注册:

```python
from ghostos.abcd import Shell, Conversation, Ghost

shell: Shell = ...
my_ghost: Ghost = ...

conversation = shell.sync(my_ghost)

# register here. usually not necessary
conversation.container().register(...)

```

## Meta-Agent

`GhostOS` 会提供一个 `MossAgent` 用来生成其它的 `MossAgent`, 也就是 Meta-Agent.
目前还在开发测试中. 