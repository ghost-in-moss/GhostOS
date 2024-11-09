from typing import Optional, TYPE_CHECKING, List, Tuple, Dict
from abc import ABC, abstractmethod
from ghostos.entity import ModelEntity, EntityMeta, EntityFactory
from ghostos.container import Container
from ghostos.identifier import Identical, Identifier
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.modules import Modules
from ghostos.contracts.configs import Configs
from ghostos.core.runtime import Session, Event
from ghostos.core.messages import Message, Role
from ghostos.core.moss import MossCompiler
from ghostos.core.llms import LLMs
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    # 避免 python 文件管理风格导致的循环依赖.
    from ghostos.core.ghosts.utils import Utils
    from ghostos.core.ghosts.shells import Shell
    from ghostos.core.ghosts.thoughts import Mindset, Thought
    from ghostos.core.ghosts.schedulers import MultiTask, Taskflow, Replier
    from ghostos.core.ghosts.operators import Operator
    from ghostos.contracts.workspace import Workspace
    from ghostos.core.ghosts.actions import Action

__all__ = ['Ghost', 'Inputs', 'GhostConf']


class Inputs(BaseModel):
    """
    定义一个标准的请求协议.
    """

    trace_id: str = Field(
        default="",
        description="inputs 的 trace id, 应该记录到日志中, 贯穿整个流程.",
    )
    session_id: str = Field(
        description="session id",
    )

    ghost_id: str = Field(
        description="ghost id",
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


class GhostConf(ModelEntity, Identical, ABC):
    """
    configuration of the ghost
    """

    @abstractmethod
    def root_thought_meta(self) -> EntityMeta:
        pass


class Ghost(ABC):

    @abstractmethod
    def conf(self) -> GhostConf:
        """
        get conf instance.
        """
        pass

    @staticmethod
    def role() -> str:
        """
        role of this ghost instance.
        """
        return Role.ASSISTANT.value

    def identifier(self) -> Identifier:
        task = self.session().task()
        if task.assistant:
            return task.assistant
        return self.conf().identifier()

    @abstractmethod
    def trace(self) -> Dict[str, str]:
        """
        trance of the current ghost instance.
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
    def init_operator(self, event: "Event") -> Tuple["Operator", int]:
        """
        :param event: the initialize event. should set the event to ghost container.
        :return: the operator and max_operator_count
        """
        pass

    @abstractmethod
    def init_event(self) -> Optional["Event"]:
        """
        the origin event from init_operator
        """
        pass

    @abstractmethod
    def meta_prompt(self) -> str:
        """
        meta prompt of the ghost
        return: prompt string
        """
        pass

    def system_prompt(self) -> str:
        """
        system prompt of the ghost.
        """
        task = self.session().task()
        # task assistant meta prompt is higher priority
        if task.assistant:
            meta_prompt = task.assistant.meta_prompt
            return meta_prompt
        meta_prompt = self.meta_prompt()
        shell_prompt = self.shell().status_description()
        content = "\n\n".join([meta_prompt, shell_prompt])
        return content.strip()

    def actions(self) -> List["Action"]:
        """
        ghost default actions
        """
        session = self.session()
        if session.task().task_id == session.update_prompt().main_task_id:
            return list(self.shell().actions())
        return []

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
    def mindset(self) -> "Mindset":
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
    def llms(self) -> LLMs:
        pass

    @abstractmethod
    def entity_factory(self) -> EntityFactory:
        """
        A factory that can make entity instances.
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
    def replier(self) -> "Replier":
        """
        a simple replier to reply the origin event
        """
        pass

    @abstractmethod
    def moss(self) -> "MossCompiler":
        """
        实例化一个 moss compiler.
        """
        pass

    @abstractmethod
    def workspace(self) -> "Workspace":
        """
        返回 Ghost 所持有的文件空间.
        这里面的文件都是 Ghost 可以管理的.
        """
        pass

    @abstractmethod
    def configs(self) -> Configs:
        """
        Configs
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
    def save(self) -> None:
        """
        Ghost 完成运行.
        """
        pass

    @abstractmethod
    def done(self) -> None:
        """
        1. save session.
        2. unlock task
        3. send final pack
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        主动做垃圾回收的准备.
        避免运行时的内存泄漏.
        """
        pass
