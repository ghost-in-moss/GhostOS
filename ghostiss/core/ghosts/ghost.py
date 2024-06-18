from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar, Optional, Dict, Any
from ghostiss.context import Context
from ghostiss.contracts.logger import LoggerItf
from ghostiss.entity import Entity, EntityDriver, EntityDriver, Normalized, MetaFactory

if TYPE_CHECKING:
    from ghostiss.container import Container
    from ghostiss.core.messages import Message
    from ghostiss.core.messenger import Messenger
    from ghostiss.core.kernel.kernel import Kernel
    from ghostiss.core.ghosts.envs import Envs
    from ghostiss.core.ghosts.events import EVENT_TYPES
    from ghostiss.core.ghosts.runtime import Runtime, Task
    from ghostiss.core.ghosts.shell import ShellItf
    from ghostiss.core.ghosts.ideas import Ideas
    from ghostiss.core.ghosts.configs import Configs
    from ghostiss.core.ghosts.libraries import Libraries
    from ghostiss.core.ghosts.operators import Operator


class TaskCtx(Context):
    """
    ghost 运行的上下文.
    """

    def __init__(
            self,
            ctx: Context,
            task: "Task",
            envs: "Envs",
            logger: "LoggerItf",
            messenger: "Messenger",
            trace: Dict,
    ):
        self._ctx = ctx
        self.task = task
        """当前任务的状态, 如果操作数据变更, 会影响后续的逻辑."""

        self.envs: "Envs" = envs
        self.logger: "LoggerItf" = logger
        self.messenger: "Messenger" = messenger
        self._trace = trace

    @abstractmethod
    def new(self, task: "Task", trace: Dict) -> "TaskCtx":
        _trace = self._trace.copy()
        _trace.update(trace)
        return TaskCtx(self._ctx, task, self.envs, self.logger.with_trace(_trace), self.messenger, _trace)

    def trace(self) -> dict:
        return self._trace

    def get(self, key: str) -> Optional[Any]:
        return self._ctx.get(key)

    def err(self) -> Optional[Exception]:
        return self._ctx.err()

    def fail(self, error: Exception) -> Optional[Exception]:
        return self._ctx.fail(error)

    def done(self) -> bool:
        return self._ctx.done()

    def life_left(self) -> float:
        return self._ctx.life_left()


class GhostMeta(Entity, ABC):
    pass


GHOST_META_TYPE = TypeVar('GHOST_META_TYPE', bound=GhostMeta)


class Ghost(EntityDriver[GHOST_META_TYPE], ABC):

    # --- consciousness --- #

    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def instructions(self) -> str:
        pass

    @property
    @abstractmethod
    def root_mind(self) -> Normalized:
        pass

    # --- components --- #

    @property
    @abstractmethod
    def container(self) -> 'Container':
        pass

    @property
    @abstractmethod
    def kernel(self) -> 'Kernel':
        pass

    @property
    @abstractmethod
    def runtime(self) -> 'Runtime':
        pass

    @property
    @abstractmethod
    def shell(self) -> 'ShellItf':
        pass

    @property
    @abstractmethod
    def libraries(self) -> 'Libraries':
        pass

    @property
    @abstractmethod
    def ideas(self) -> 'Ideas':
        pass

    @property
    @abstractmethod
    def configs(self) -> 'Configs':
        """
        配置模块, 读取 Ghost 的专属配置.
        """
        pass

    # --- methods --- #

    @abstractmethod
    def new_task_ctx(
            self,
            ctx: "Context",
            messenger: "Messenger",
            task: "Task",
            env: "Envs",
            timeout: int = 0,
    ) -> TaskCtx:
        """
        create a task context
        """
        pass

    # --- flows --- #

    def facade(self) -> "Facade":
        """
        将常用方法封装到 facade 里. 也方便未来通过继承的方式重写核心运行逻辑.
        """
        return Facade(self)

    @abstractmethod
    def sleep(self, seconds: float = 0, waken: Optional[Message] = None) -> None:
        pass


G = TypeVar('G', bound=Ghost)


class GhostMaker(Generic[G], EntityDriver[G], ABC):
    pass


class Matrix(MetaFactory[Ghost], ABC):

    @abstractmethod
    def kernel(self) -> Kernel:
        pass

    @abstractmethod
    def runtime(self, ghost_id: str) -> Runtime:
        pass


class Facade:
    """
    将常见方法记录到一个 facade 类里. 这样方便未来继承修改.
    """

    def __init__(self, g: "Ghost"):
        self.ghost: "Ghost" = g

    def run_event(self, ctx: "TaskCtx", event: "EVENT_TYPES") -> None:
        """
        基于一个 event 运行.
        """
        op = self.fire_event(ctx, event)
        if op is not None:
            self.run_operators(ctx, op)

    def fire_event(self, ctx: "TaskCtx", event: "EVENT_TYPES") -> Optional["Operator"]:
        """
        运行一个 event.
        """
        locker = None
        task_id = ctx.task.task_id
        g = self.ghost
        try:
            locker = g.runtime.lock_task(task_id)
            if locker is None:
                # 如果没有上锁成功的话, 将
                # ctx.logger.info("todo")
                g.runtime.put_task_event(task_id, event.normalize())
                return None

            idea = g.ideas.new_entity(ctx.task.idea)
            if idea is None:
                # todo
                raise NotImplemented("todo")

            return idea.on_event_meta(ctx, g, event)
        except Exception as err:
            ctx.fail(err)
        finally:
            if locker:
                g.runtime.release_task(ctx.task.task_id, locker)

    def run_operators(self, ctx: "TaskCtx", op: "Operator") -> None:
        """
        触发 operators 并运行.
        """
        while op is not None:
            # todo 日志.
            op = op.run(ctx, self.ghost)
