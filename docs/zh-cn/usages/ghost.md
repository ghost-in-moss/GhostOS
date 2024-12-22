# Ghost

`Ghost` 是 `GhostOS` 的名字来源, 是智能体的 `最小有状态单元`. 
这个词来自于 [Ghost In the Shell](https://en.wikipedia.org/wiki/Ghost_in_the_Shell).

在 `GhostOS` 的架构设计中, 一个智能体集群由许多个 `Ghost` 单元构成, 每个 `Ghost` 拥有自身的状态, 记忆和上下文 (Session),
它们之间可以通过 `EventBus` 进行全异步的通讯. 

![architecture](../../assets/architecture.png)


## Why the word `Ghost` instead of `Agent`

在作者的架构设想中, `Agent` 是对于用户而言的单一实体或交互界面.
它是拥有躯体 (也就是 Shell) 的. 

但在一个躯体内运行的, 可能是一个 Multi-Agent (或 Multi-Ghost) 集群, 用于:

* 并行执行多个任务.
* 模拟不同的角色进行思维推演.
* 异步地解决长耗时任务. 

我们举一个简单的例子: 

1. 用户对话的 `Agent`, 默认运行快速的 `gpt-4o` 模型来控制对话.
2. 当用户问到复杂问题时, 主 ghost 调用 `gpt-o3` 运行了一个长达 30秒的思考过程.
3. 在这 30 秒内, 主 agent 并未阻塞, 而是继续和用户对话. 
4. 30 秒后, 主 agent 拿到异步回调的结果, 并告知用户. 

在这个例子中, 并行执行和事件总线是最关键的功能. 所以 Ghost 可以是: 

* 用户对话的一个 Agent
* 主 Agent 开启的一个分身, 使用不同的模型, 专注于某个任务或思考
* 后台运行的一个 workflow
* 后台运行的自动机器人
* 一个独立的脚本
* 具身智能体的某一个可以执行自然语言命令的组件
* 对自身运行效果进行反思的后台程序

它们共同的特点是: 
* 大模型驱动
* 拥有多轮运行能力
* 类似操作系统的 thread, 是最小的同步运行单元, 拥有独立的上下文

## Ghost Driver

在 `GhostOS` 中, `Ghost` 需要通过至少两个类来定义其原型. 

 [Ghost](https://github.com/ghost-in-moss/GhostOS/ghostos/abcd/concepts.py) 类: 

```python

class Ghost(Identical, EntityClass, ABC):
    """
    the class defines the model of a kind of ghosts.
    four parts included:
    1. configuration of the Ghost, which is Ghost.__init__. we can predefine many ghost instance for special scenes.
    2. context is always passed by the Caller of a ghost instance. each ghost class has it defined context model.
    3. goal is the static output (other than conversation messages) of a ghost instance.
    4. driver is
    """

    ArtifactType: ClassVar[Optional[Type]] = None
    """ the model of the ghost's artifact, is completing during runtime"""

    ContextType: ClassVar[Optional[Type[ContextType]]] = None
    """ the model of the ghost's context, is completing during runtime'"""

    DriverType: ClassVar[Optional[Type[GhostDriver]]] = None
    """ separate ghost's methods to the driver class, make sure the ghost is simple and clear to other ghost"""

```

[GhostDriver](https://github.com/ghost-in-moss/GhostOS/ghostos/abcd/concepts.py) 类: 

```python

class GhostDriver(Generic[G], ABC):
    """
    Ghost class is supposed to be a data class without complex methods definitions.
    so it seems much clear when prompt to the LLM or user-level developer.
    when LLM is creating a ghost class or instance, we expect it only see the code we want it to see,
    without knowing the details codes of it, for safety / fewer tokens / more focus or other reasons.

    so the methods of the ghost class defined in this class.
    only core developers should know details about it.
    """

    def __init__(self, ghost: G) -> None:
        self.ghost = ghost

    def make_task_id(self, parent_scope: Scope) -> str:
        """
        generate unique instance id (task id) of the ghost instance.
        """
        pass

    @abstractmethod
    def get_artifact(self, session: Session) -> Optional[G.ArtifactType]:
        """
        generate the ghost goal from session_state
        may be the Goal Model is a SessionStateValue that bind to it.

        The AI behind a ghost is not supposed to operate the session object,
        but work on the goal through functions or Moss Injections.
        """
        pass

    @abstractmethod
    def get_instructions(self, session: Session) -> str:
        """
        get system instructions of the ghost.
        usually used in client side.
        """
        pass

    @abstractmethod
    def actions(self, session: Session) -> List[Action]:
        """
        return actions that react to the streaming output of llm
        """
        pass

    @abstractmethod
    def providers(self) -> Iterable[Provider]:
        """
        ghost return conversation level container providers.
        the provider that is not singleton will bind to session also.
        """
        pass

    @abstractmethod
    def parse_event(
            self,
            session: Session,
            event: Event,
    ) -> Union[Event, None]:
        """
        intercept the ghost event
        :returns: if None, the event will be ignored
        """
        pass

    @abstractmethod
    def on_creating(self, session: Session) -> None:
        """
        when the ghost task is created first time.
        this method can initialize the thread, pycontext etc.
        """
        pass

    @abstractmethod
    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        """
        all the state machine is only handling session event with the predefined operators.
        """
        pass

    @abstractmethod
    def truncate(self, session: Session) -> GoThreadInfo:
        """
        truncate the history messages in the thread
        """
        pass

```

这么做的动机是, `GhostOS` 使用 `Code As Prompt` 的思路直接将代码反射成大模型看到的 Prompt. 
在 Mutli-Agent 架构中, `GhostDriver` 的细节代码对于使用它的 Agent 而言是不必要的. 
将数据结构为主的 `Ghost` 和运行逻辑为主的 `GhostDriver` 进行拆分, 有利于其它 Agent 更简洁地理解如何构建一个 Agent. 


## Ghost Context

[Context](https://github.com/ghost-in-moss/GhostOS/ghostos/abcd/concepts.py) 可以理解为 `Ghost` 运行时的入参.
它可以接受强类型的数据结构, 同时生成 system prompt 提供给大模型, 用来理解上下文. 同时大模型可以将 context 作为一个变量来操作.

Context 实现了 [Prompter](../concepts/prompter.md), 它本质上是类似 `DOM` 的 `Prompt Object Model` 数据结构, 
需要用强类型的参数反射出 system instruction, 作为 prompt 的一部分提交给 LLM. 

Context 通常用来实现: 
* 具身智能体自己身体的状态, 对周围环境的识别
* AI 应用在端侧 (比如 IDE) 的状态, 和用户同步认知. 
* 某些动态变更的入参数据, 比如一个 AI 运维看到的监控面板. 

作为入参传递给对话: 

```python
from pydantic import Field
from ghostos.abcd import Context, Conversation, Ghost


class ProjectContext(Context):
    directory: str = Field(description="the root directory of a project")


project_agent: Ghost = ...
project_context: ProjectContext = ...
conversation: Conversation = ...

conversation.talk("your query to edit the project", project_context)
```

有必要的话, 可以让 MossAgent 通过 `Moss` 去操作一个 Context: 

```python
from ghostos.abcd import Context
from ghostos.core.moss import Moss as Parent
from pydantic import Field

class ProjectContext(Context):
    directory: str = Field(description="the root directory of a project")


class Moss(Parent):
    
    # the moss agent can operate this ctx instance.
    ctx: ProjectContext
```


## Ghost Artifact

[Artifact](https://github.com/ghost-in-moss/GhostOS/ghostos/abcd/concepts.py) 可以理解为 `Ghost` 运行时的出参.
只不过这个出参是可以一直变动的. 

通过 `Conversation` 可以拿到 `Ghost` 运行时的 `Artifact` 对象, 用于端侧的渲染: 

```python
from ghostos.abcd import Conversation, Ghost, Shell


my_ghost: Ghost = ...
shell: Shell = ...
conversation: Conversation = shell.sync(ghost=my_ghost)

conversation.talk(...)

# get artifact 
artifact = conversation.get_artifact()
```

在 `MossAgent` 中, 可以将 `Artifact` 挂载在 `Moss` 对象上让大模型操作. 


## ChatBot and MossAgent

[Chatbot](chatbot.md) 和 [MossAgent](moss_agent.md) 是 `GhostOS` 项目中对 Ghost 的基础实现. 详见相关文档. 

## More Ghosts

developing...