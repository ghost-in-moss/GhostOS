from typing import Optional, TYPE_CHECKING, List, Type
from abc import ABC, abstractmethod
from ghostiss.entity import Entity, EntityMeta
from ghostiss.container import Container
from ghostiss.abc import Identifiable, Identifier
from ghostiss.contracts.logger import LoggerItf
from ghostiss.contracts.modules import Modules
from ghostiss.contracts.storage import Storage
from ghostiss.core.session import Session, Threads, Tasks, Processes, EventBus, Event
from ghostiss.core.messages import Message
from ghostiss.core.moss import MossCompiler
from ghostiss.core.llms import LLMs, Chat
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    # 避免 python 文件管理风格导致的循环依赖.
    from ghostiss.core.ghosts.utils import Utils
    from ghostiss.core.ghosts.shells import Shell
    from ghostiss.core.ghosts.thoughts import Thoughts
    from ghostiss.core.ghosts.schedulers import MultiTask, Taskflow

__all__ = ['Ghost', 'Inputs']


class Inputs(BaseModel):
    """
    定义一个标准的请求协议.
    """

    trace: str = Field(
        default="",
        description="inputs 的 trace id, 应该记录到日志中, 贯穿整个流程.",
    )

    ghost_meta: EntityMeta = Field(
        description="ghost 的配置信息. 指定了响应请求的 Ghost.",
    )

    messages: List[Message] = Field(
        description="本轮请求真正的输入数据. 不应该为空. "
    )

    process_id: Optional[str] = Field(
        default=None,
        description="指定响应时进程的 id. 如果目标进程存在, 则用它响应. ",
    )
    task_id: Optional[str] = Field(
        default=None,
        description="指定响应的 task id. 如果目标 task 存在, 则用它来响应. ",
    )
    thought_meta: Optional[str] = Field(
        default=None,
        description="",
    )


class Ghost(Entity, Identifiable, ABC):

    @abstractmethod
    def identifier(self) -> Identifier:
        """
        Ghost 的自我描述. 可能用来生成 prompt.
        """
        pass

    @abstractmethod
    def to_entity_meta(self) -> EntityMeta:
        """
        用来生成 Ghost Meta 保存到 Process 里.
        """
        pass

    @abstractmethod
    def on_inputs(self, inputs: Inputs) -> Optional["Event"]:
        """
        对请求进行预处理, 如果返回一个事件, 则触发事件响应流程.
        可以在这个环节使用管道的方式预处理输入消息, 比如检查消息体是否过大, 或者是否触发一个命令.
        :param inputs: 输入消息.
        :return: 是否正式触发一个事件.
        """
        pass

    @abstractmethod
    def update_chat(self, chat: Chat) -> Chat:
        """
        将 Ghost 的 meta prompt 注入到 Chat 里.
        update_chat 应该包含:
        1. 注入 ghost 的自我认知.
        2. 注入 ghost 的元指令.
        3. 注入 shell 的描述.
        4. 注入 thought 无关的通用工具.
        """
        pass

    @abstractmethod
    def container(self) -> Container:
        """
        ghost 持有的 IoC 容器.
        """
        pass

    @abstractmethod
    def session(self) -> Session:
        """
        会话的构建, 在 Ghost In Shell 的架构里, Session 要先于 Ghost 构建.
        由于全异步 Session 作为基础设施, 所以 Ghost 每次运行时都是在一个特定的 task 里.
        """
        pass

    @abstractmethod
    def shell(self) -> "Shell":
        """
        返回 ghost 所属的 shell 抽象.
        持有了对端设备交互能力的抽象.
        """
        pass

    @abstractmethod
    def thoughts(self) -> "Thoughts":
        """
        thoughts 管理所有的 Thoughts, 仍可以用来召回.
        """
        pass

    @abstractmethod
    def modules(self) -> "Modules":
        """
        基于 modules 可以管理所有类库.
        通过预加载, 可以搜索存在的类库.
        """
        pass

    @abstractmethod
    def logger(self) -> "LoggerItf":
        """
        返回基于当前上下文生成的 logger 实例.
        """
        pass

    @abstractmethod
    def multitasks(self) -> "MultiTask":
        """
        当前 Task 的多任务管理模块.
        提供原语管理基础的多任务调度.
        作为基础的调度模块, 可供其它类库的封装.
        """
        pass

    @abstractmethod
    def taskflow(self) -> "Taskflow":
        """
        对当前 Task 自身的状态管理器.
        提供原语管理自身的任务调度.
        """
        pass

    @abstractmethod
    def moss(self) -> "MossCompiler":
        """
        实例化一个 moss compiler.
        """
        pass

    @abstractmethod
    def workspace(self) -> Storage:
        """
        返回 Ghost 所持有的文件空间.
        这里面的文件都是 Ghost 可以管理的.
        """
        pass

    @abstractmethod
    def finish(self, err: Optional[Exception]) -> None:
        """
        Ghost 运行时用统一的 Finish 方法来结束一个周期.
        用来存储状态变更, 或者处理异常.
        :param err: 记录运行时异常.
        """
        pass

    @abstractmethod
    def utils(self) -> "Utils":
        """
        Ghost 的
        """
        pass

    @classmethod
    def contracts(cls) -> List[Type]:
        """
        Ghost 完成初始化后, IoC container 必须要提供的抽象列表.
        可以用于检查 Ghost 的初始化是否完成.
        """
        from ghostiss.core.ghosts.shells import Shell
        from ghostiss.core.ghosts.thoughts import Thoughts
        from ghostiss.core.ghosts.schedulers import MultiTask, Taskflow
        return [

            LoggerItf,  # 日志模块. 为了动态传递一些数据, 所以用 LoggerItf

            Ghost,  # ghost 自身.
            Shell,  # shell 的封装.
            MossCompiler,  # 生成 MossCompiler

            Thoughts,  # 管理所有的 thought.
            Modules,  # 安全管理下的 Modules 模块.
            LLMs,  # 大模型的 API 集成.
            MultiTask,  # 多任务管理的原语.
            Taskflow,  # 当前任务自身管理的原语.

            Session,  # 状态管理.
            # unsafe 的底层模块.
            Threads,
            Tasks,
            Processes,
            EventBus,
        ]

    @abstractmethod
    def destroy(self) -> None:
        """
        主动做垃圾回收的准备.
        避免运行时的内存泄漏.
        """
        pass
