from typing import List, Optional, Callable
from abc import ABC, abstractmethod
from ghostiss.entity import EntityMeta
from ghostiss.core.messages import Message, Stream
from ghostiss.core.session import Runtime
from ghostiss.core.session.tasks import Task, TaskState
from ghostiss.core.session.processes import Process
from ghostiss.core.ghosts import Ghost
from ghostiss.core.ghosts.operators import handle_event
from ghostiss.core.session.events import EventBus, Event, DefaultEventType
from ghostiss.container import Container
from pydantic import BaseModel, Field


class Inputs(BaseModel):
    """
    定义一个标准的请求协议.
    """

    trace: str = Field(default="")
    ghost_meta: EntityMeta = Field()
    process_id: Optional[str] = Field(default=None)
    task_id: Optional[str] = Field(default=None)
    thought_id: Optional[str] = Field(default=None)
    messages: List[Message]


class GhostInShellSystem(ABC):

    def run(self, inputs: Inputs, deliver: Stream) -> None:
        """
        处理同步请求. deliver 的实现应该在外部.
        :param inputs:
        :param deliver:
        :return:
        """
        runtime = self.runtime()
        process = runtime.processes.get_ghost_process(inputs.ghost_meta['id'])
        if process is None:
            process = self.create_process(ghost_meta=inputs.ghost_meta)
            runtime.processes.save_process(process)
        if not runtime.tasks.has_task(process.main_task_id):
            task = self.create_process_main_task(process)
        else:
            task = runtime.tasks.lock_task(process.main_task_id)

        if not task.locker:
            # 没有抢到锁.
            return self.on_task_lock_failed(deliver, task, inputs)

        event = DefaultEventType.INPUT.new(
            eid=inputs.trace,
            task_id=inputs.task_id if inputs.task_id else process.main_task_id,
            messages=inputs.message,
        )

        # 异步运行
        self.async_run(lambda: self.run_task_event(task, event, deliver))

    @abstractmethod
    def on_task_lock_failed(self, deliver: Stream, task: Task, inputs: Inputs) -> None:
        pass

    @abstractmethod
    def create_process(self, ghost_meta: EntityMeta) -> Process:
        pass

    @abstractmethod
    def create_process_main_task(self, process: Process) -> Task:
        pass

    @abstractmethod
    def container(self) -> Container:
        """
        全局默认的 container.
        """
        pass

    @abstractmethod
    def make_ghost(self, runtime: Runtime, ghost_meta: EntityMeta, deliver: Optional[Stream]) -> Ghost:
        pass

    @abstractmethod
    def get_ghost(self, ghost_id: str) -> Optional[Ghost]:
        pass

    @abstractmethod
    def register_ghost(self, ghost_meta: EntityMeta) -> None:
        pass

    @abstractmethod
    def runtime(self) -> Runtime:
        pass

    @abstractmethod
    def eventbus(self) -> EventBus:
        pass

    @abstractmethod
    def stopped(self) -> bool:
        pass

    @abstractmethod
    def wait(self) -> None:
        pass

    @abstractmethod
    def async_run(self, caller: Callable) -> None:
        pass

    def background_run(self) -> None:
        while not self.stopped():
            self.async_run(self.background_run_event)

    @abstractmethod
    def background_task_max_run(self) -> int:
        pass

    def background_run_event(self) -> None:
        """
        在 background_run 里运行一轮.
        :return:
        """
        eventbus = self.eventbus()
        e = eventbus.pop_global_event()
        if e is None:
            return None
        runtime = self.runtime()
        turn = 0
        max_run = self.background_task_max_run()
        while e is not None and (max_run <= 0 or turn < max_run):
            task = runtime.tasks.lock_task(e.task_id)
            if task is None:
                # 不需要执行了.
                return None
            if TaskState.is_dead(task.state):
                # todo
                return None
            self.run_task_event(task, e, None)
            # 继续拉取事件.
            # todo: log
            e = eventbus.pop_task_event(task.task_id)

    def run_task_event(self, task: Task, e: Event, deliver: Optional[Stream] = None) -> None:
        """
        运行一个任务的事件. 这个方法应该放到某个 thread 里运行.
        :param deliver:
        :param task:
        :param e:
        :return:
        """
        runtime = self.runtime()
        process = runtime.processes.get_process(task.process_id)
        if not process.is_alive():
            # todo: log
            return None
        if TaskState.is_dead(task.state):
            # todo: log
            return None

        ghost = self.make_ghost(runtime=runtime, ghost_meta=process.ghost_meta, deliver=deliver)
        err = None
        try:
            op = handle_event(ghost, e)
            while op is not None:
                # todo: log and try except
                op = op.run(ghost)
        except Exception as exp:
            err = exp
        finally:
            ghost.finish(err)


Ghostiss = GhostInShellSystem
"""定义一个别名"""
