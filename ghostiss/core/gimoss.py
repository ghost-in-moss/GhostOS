from typing import List, Optional, Callable, Dict
from abc import ABC, abstractmethod
from ghostiss.entity import EntityMeta
from ghostiss.core.messages import Message, Stream
from ghostiss.core.session import Session, Tasks, TaskState
from ghostiss.core.ghosts import Ghost
from ghostiss.core.session.events import EventBus, Event, DefaultEventType
from ghostiss.contracts.logger import LoggerItf
from ghostiss.container import Container
from ghostiss.helpers import uuid
from pydantic import BaseModel, Field


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


class GhostInMOSS(ABC):
    """
    Ghost In MOSS (Model-oriented Operating System Simulation)
    """

    @abstractmethod
    def container(self) -> Container:
        """
        全局默认的 container.
        """
        pass

    @abstractmethod
    def logger(self) -> LoggerItf:
        pass

    @abstractmethod
    def find_session(self, upstream: Stream, task_id: str) -> Optional[Session]:
        pass

    @abstractmethod
    def find_or_create_session(
            self, ghost_meta: EntityMeta, upstream: Stream, task_id: str
    ) -> Session:
        """
        根据请求, 实例化 Session. 一切功能的起点.
        :param ghost_meta: 基于 ghost_meta 配置项生成 Session. ghost_meta 主要用来生成进程.
        :param upstream: 上游的消息通道. 接收方应该于外部定义. 对于异步运行的 Session,
                         上游的 upstream 应该不发送消息到端, 除非支持多流协议.
        :param task_id: 指定使用哪个 task id 来获取 session. 不存在的话, 会创建一个.
        :exception: 运行错误不应该返回 None, 而应该抛出异常.
        """
        pass

    @abstractmethod
    def eventbus(self) -> EventBus:
        """
        持有 EventBus.
        """
        pass

    @abstractmethod
    def create_ghost(self, session: Session) -> Ghost:
        """
        使用 Session 实例化当前的 Ghost.
        """
        pass

    def on_inputs(self, inputs: Inputs, upstream: Stream) -> None:
        """
        处理同步请求. deliver 的实现应该在外部.
        这个方法是否异步执行, 也交给外部判断.
        :param inputs: 同步请求的参数.
        :param upstream: 对上游输出的 output
        """
        if not inputs.trace:
            inputs.trace = uuid()
        task_id = inputs.task_id if inputs.task_id else inputs.trace
        session = self.find_or_create_session(inputs.ghost_meta, upstream, task_id)
        ghost = self.create_ghost(session)
        event = DefaultEventType.INTERCEPT.new(
            eid=inputs.trace,
            task_id=inputs.task_id,
            messages=inputs.message,
        )
        # 无锁操作, 拦截事件. 只会运行一轮.
        self.handle_event(ghost, event)

    @abstractmethod
    def dispatch(self, caller: Callable, *, timeout: float, args: List, kwargs: Dict) -> Callable:
        """
        执行一个需要消耗资源的运行逻辑, 分配资源和超时.
        :param caller:
        :param timeout:
        :param args:
        :param kwargs:
        :return:
        """
        pass

    def handle_event(self, ghost: Ghost, e: Event) -> None:
        """
        运行事件.
        """
        err = None
        try:
            # handle event 方法会获取锁.
            op = ghost.utils().handle_event(e)
            while op is not None:
                # todo: log and try except
                op = op.run(ghost)
        except Exception as exp:
            # todo
            err = exp
        finally:
            ghost.finish(err)
            ghost.destroy()

    def background_run_event(self, upstream: Stream) -> bool:
        """
        尝试从 eventbus 里 pop 一个事件, 然后运行.
        外部系统应该管理所有资源分配, 超时的逻辑.
        :return: False if no event is popped.
        :exception: todo
        """
        eventbus = self.eventbus()
        e = eventbus.pop_global_event()
        if e is None:
            return False

        session = self.find_session(upstream, e.task_id)
        if session is None:
            # todo: 记录异常, background run 的事件不应该 task 不存在.
            return True
        # 耗时长的逻辑先执行.
        ghost = self.create_ghost(session)
        if e.block and not session.refresh_lock():
            # session 尝试获取或更新锁, 如果获取失败, 意味着有别的进程正在运行这个 task. 让它去处理.
            return True
        task = session.task()
        self.dispatch(self.handle_event, timeout=task.timeout, args=[ghost, e], kwargs={})
        return True
