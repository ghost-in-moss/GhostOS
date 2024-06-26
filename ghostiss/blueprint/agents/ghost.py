from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Dict, Any
from ghostiss.contracts.logger import LoggerItf
from ghostiss.entity import Entity, EntityMeta, EntityFactory

if TYPE_CHECKING:
    from ghostiss.container import Container
    from ghostiss.blueprint.messages import Message
    from ghostiss.blueprint.messenger import Messenger
    from ghostiss.blueprint.kernel.kernel import Kernel
    from ghostiss.blueprint.agents.envs import Envs
    from ghostiss.blueprint.agents.events import EVENT_TYPES
    from ghostiss.blueprint.agents.runtime import Runtime, Task
    from ghostiss.blueprint.agents.shell import Shell
    from ghostiss.blueprint.agents.minds import Ideas
    from ghostiss.contracts.configs import Configs
    from ghostiss.blueprint.agents.libraries import Libraries
    from ghostiss.blueprint.agents.operators import Operator


class TaskCtx(Context):
    """
    ghost 运行的上下文.
    """

    def __init__(
            self,
            task: "Task",
            envs: "Envs",
            logger: "LoggerItf",
            messenger: "Messenger",
            trace: Dict,
    ):
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


class Ghost(Entity, ABC):

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
    def root_mind(self) -> EntityMeta:
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
    def shell(self) -> 'Shell':
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

    # --- flows --- #

    def facade(self) -> "Facade":
        """
        将常用方法封装到 facade 里. 也方便未来通过继承的方式重写核心运行逻辑.
        """
        return Facade(self)

    @abstractmethod
    def sleep(self, seconds: float = 0, waken: Optional[Message] = None) -> None:
        pass


class Matrix(EntityFactory[Ghost], ABC):
    pass
    # @abstractmethod
    # def kernel(self) -> Kernel:
    #     pass
    #
    # @abstractmethod
    # def runtime(self, ghost_id: str) -> Runtime:
    #     pass


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
                g.runtime.put_task_event(task_id, event.to_entity_meta())
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
