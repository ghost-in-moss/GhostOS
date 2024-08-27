from typing import Optional, TYPE_CHECKING, List, Tuple
from abc import ABC, abstractmethod
from ghostos.entity import Entity, EntityMeta
from ghostos.container import Container
from ghostos.abc import Identifiable, Identifier
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.modules import Modules
from ghostos.contracts.storage import Storage
from ghostos.core.session import Session, Event
from ghostos.core.messages import Message, Caller, Role
from ghostos.core.moss import MossCompiler
from ghostos.core.llms import Chat
from ghostos.helpers import generate_import_path
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    # 避免 python 文件管理风格导致的循环依赖.
    from ghostos.core.ghosts.utils import Utils
    from ghostos.core.ghosts.shells import Shell
    from ghostos.core.ghosts.thoughts import Thoughts, Thought
    from ghostos.core.ghosts.schedulers import MultiTask, Taskflow
    from ghostos.core.ghosts.operators import Operator

__all__ = ['Ghost', 'Inputs']


class Inputs(BaseModel):
    """
    定义一个标准的请求协议.
    """

    trace: str = Field(
        default="",
        description="inputs 的 trace id, 应该记录到日志中, 贯穿整个流程.",
    )
    session_id: str = Field(
        description="session id",
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


class GhostConf(BaseModel, Entity, ABC):

    def ghost_id(self) -> str:
        pass

    def to_entity_meta(self) -> EntityMeta:
        id_ = self.ghost_id()
        type_ = generate_import_path(self.__class__)
        return EntityMeta(
            id=id_,
            type=type_,
            data=self.model_dump(exclude_defaults=True),
        )

    @abstractmethod
    def make_ghost(self, container: Container, session: Session) -> "Ghost":
        """
        实例化 Ghost.
        :param container: 需要传入的外部容器.
        :param session: Session 优先于 Ghost 生成.
        :return:
        """
        pass

    def instance_ghost(self, container: Container, session: Session) -> "Ghost":
        """
        实例化 Ghost.
        :param container:
        :param session:
        """
        ghost = self.make_ghost(container, session)
        identifier = ghost.identifier()
        session.with_ghost(name=identifier.name, role=ghost.role())
        return ghost


class Ghost(Identifiable, ABC):

    @abstractmethod
    def identifier(self) -> Identifier:
        """
        Ghost 的自我描述. 可能用来生成 prompt.
        """
        pass

    def role(self) -> str:
        return Role.ASSISTANT.value

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
    def init_operator(self, event: "Event") -> Tuple["Operator", int]:
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
    def root_thought(self) -> "Thought":
        """
        Ghost 的根节点思维单元.
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
    def taskflow(self, caller: Optional[Caller] = None) -> "Taskflow":
        """
        对当前 Task 自身的状态管理器.
        提供原语管理自身的任务调度.
        :param caller: 如果在 llm caller 中运行 taskflow, 可以将 caller 带上, 用来生成 function 类型的消息.
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
    def utils(self) -> "Utils":
        """
        Ghost 的
        """
        pass

    @abstractmethod
    def fail(self, err: Optional[Exception]) -> None:
        """
        Ghost 运行时用统一的 Finish 方法来结束一个周期.
        用来存储状态变更, 或者处理异常.
        :param err: 记录运行时异常.
        """
        pass

    @abstractmethod
    def done(self) -> None:
        """
        Ghost 完成运行.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        主动做垃圾回收的准备.
        避免运行时的内存泄漏.
        """
        pass
