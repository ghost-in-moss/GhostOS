from typing import Optional
from abc import ABC, abstractmethod
from ghostos.entity import EntityMeta
from ghostos.core.messages import Stream
from ghostos.core.session import EventBus, Event, Tasks, Task, Process, Processes, DefaultEventType
from ghostos.core.ghosts import Ghost, GhostConf, Inputs
from ghostos.contracts.logger import LoggerItf
from ghostos.contracts.shutdown import Shutdown
from ghostos.container import Container


class GhostOS(ABC):
    """
    Ghost 自身的操作系统.
    """

    @abstractmethod
    def container(self) -> Container:
        """
        global default container.
        """
        pass

    @abstractmethod
    def register(self, ghost_conf: GhostConf) -> None:
        """
        register a ghost_conf into the container.
        :param ghost_conf: the meta of the ghost conf shall be able to create ghost in this ghost os.
        """
        pass

    @abstractmethod
    def get_ghost_meta(self, ghost_id: str) -> Optional[EntityMeta]:
        """
        get ghost meta by ghost id
        """
        pass

    @abstractmethod
    def get_or_create_process(
            self, *,
            ghost_meta: EntityMeta,
            session_id: str,
            process_id: Optional[str] = None,
            task_id: Optional[str] = None,
    ) -> Optional[Process]:
        """
        get a process from session_id, if not exists, create one.
        :param ghost_meta: to create ghost instance.
        :param session_id: session_id is the ghost instance id.
        :param process_id:
        :param task_id:
        :return:
        """
        pass

    @abstractmethod
    def make_ghost(
            self, *,
            upstream: Stream,
            process: Process,
            task: Optional[Task] = None,
            task_id: Optional[str] = None,
    ) -> Ghost:
        """
        make a ghost instance.
        :param upstream: upstream that ghost sending messages to. Each round of thought shall send a Final package.
                         once upstream is stopped, the ghost will stop as well.
        :param process: process to make ghost instance.
        :param task: if task is None, ghost will instance on the process main task.
        :param task_id: if task_id is not None, ghost will find the target task to instance on.
        """
        pass

    def on_inputs(
            self,
            inputs: Inputs,
            upstream: Stream,
            is_async: bool = False,
    ) -> None:
        """
        handle and inputs by ghostos. GhostOS will:
        1. check the inputs, intercept it if necessary
        2. wrap the inputs to a event
        3. send event to event bus
        4. handle event immediately if get the task's lock

        :param inputs: inputs to a ghost instance.
        :param upstream: the stream that ghost sending messages to.
        :param is_async: if is_async, ghost would not run, but send event only.
        """
        pass

    def background_run(self, upstream: Stream) -> None:
        """
        尝试从 EventBus 中获取一个 task 的信号, 并运行它.
        """
        pass

    @abstractmethod
    def handle_ghost_event(self, *, ghost: Ghost, event: Event) -> None:
        """
        use ghost to handle event which belongs to the ghost session.task()
        """
        pass

    @abstractmethod
    def on_error(self, error: Exception) -> bool:
        """
        :param error: handle error
        :return: raise?
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        graceful shutdown.
        """
        pass


class AbsGhostOS(GhostOS, ABC):
    """
    GhostOS abstract base class.
    """

    @abstractmethod
    def container(self) -> Container:
        """
        全局默认的 container.
        """
        pass

    def _logger(self) -> LoggerItf:
        """
        return logger instance
        """
        return self.container().force_fetch(LoggerItf)

    def _eventbus(self) -> EventBus:
        """
        返回全局的 EventBus.
        """
        return self.container().force_fetch(EventBus)

    def _processes(self) -> Processes:
        return self.container().force_fetch(Processes)

    def _tasks(self) -> Tasks:
        return self.container().force_fetch(Tasks)

    @abstractmethod
    def make_ghost(
            self, *,
            upstream: Stream,
            process: Process,
            task: Optional[Task] = None,
            task_id: Optional[str] = None,
    ) -> Ghost:
        """
        使用 Session 实例化当前的 Ghost.
        """
        pass

    def get_or_create_process(
            self, *,
            ghost_meta: EntityMeta,
            session_id: str,
            process_id: Optional[str] = None,
            task_id: Optional[str] = None,
    ) -> Optional[Process]:
        processes = self._processes()
        proc = processes.get_session_process(session_id)
        if proc is None or (process_id and process_id != proc.pid):
            proc = Process.new(
                session_id=session_id,
                ghost_meta=ghost_meta,
                process_id=process_id,
                main_task_id=task_id,
            )
        return proc

    def on_inputs(
            self,
            inputs: Inputs,
            upstream: Stream,
            is_async: bool = False,
    ) -> str:
        """
        处理同步请求. deliver 的实现应该在外部.
        这个方法是否异步执行, 也交给外部判断.
        :param inputs: 同步请求的参数.
        :param upstream: 对上游输出的 output
        :param is_async: 是否异步运行.
        :returns: task_id
        """
        # 获取基本参数.
        session_id = inputs.session_id
        ghost_meta = self.get_ghost_meta(inputs.ghost_id)
        if ghost_meta is None:
            raise NotImplementedError(f"ghost {inputs.ghost_id} does not defined")
        # 寻找已经存在的进程.
        proc = self.get_or_create_process(
            ghost_meta=ghost_meta,
            session_id=session_id,
            process_id=inputs.process_id,
            task_id=inputs.task_id,
        )

        # 生成 ghost 实例.
        ghost = self.make_ghost(upstream=upstream, process=proc, task_id=inputs.task_id)
        try:
            # pre-process input. stateless. if event is None, inputs was intercepted.
            event = ghost.on_inputs(inputs)
            if event is None:
                return ""

            # 发送事件.
            eventbus = self._eventbus()
            if not is_async:
                self.handle_ghost_event(ghost=ghost, event=event)
                ghost.done()
            else:
                ghost.done()
                eventbus.send_event(event, notify=True)
                return event.task_id
        except Exception as e:
            ghost.fail(e)
            if self.on_error(e):
                raise
        finally:
            ghost.destroy()

    def background_run(self, upstream: Stream) -> bool:
        """
        尝试从 EventBus 中获取一个 task 的信号, 并运行它.
        """
        try:
            # 暂时不传递 timeout.
            return self._background_run(upstream)
        except Exception as e:
            if self.on_error(e):
                raise

    def _background_run(self, upstream: Stream) -> bool:
        """
        尝试从 eventbus 里 pop 一个事件, 然后运行.
        外部系统应该管理所有资源分配, 超时的逻辑.
        """
        eventbus = self._eventbus()
        # at least one success.
        task_id = eventbus.pop_task_notification()
        # 没有读取到任何全局任务.
        if task_id is None:
            return False
        success = self._background_run_task(upstream=upstream, task_id=task_id)
        if not success:
            eventbus.notify_task(task_id)
        return success

    def _background_run_task(
            self, *,
            upstream: Stream,
            task_id: str,
    ) -> bool:
        """
        指定一个 task id, 尝试运行它的事件.
        :param upstream:
        :param task_id: 指定的 task id
        :return: continue?
        """
        tasks = self._tasks()
        task = tasks.get_task(task_id, lock=True)
        if task is None:
            return False
        lock = task.lock
        locked = lock is not None
        # task 没有抢到锁.
        if not locked:
            return False
        # 先创建 session.
        processes = self._processes()
        proc = processes.get_process(task.process_id)
        # process is quited
        if proc.quited:
            self._eventbus().clear_task(task_id)
            return True
        ghost = self.make_ghost(upstream=upstream, process=proc, task=task)
        try:
            if not ghost.session().refresh_lock():
                return False

            eventbus = self._eventbus()
            e = eventbus.pop_task_event(task_id)
            if e is None:
                return True
            self.handle_ghost_event(ghost=ghost, event=e)
            ghost.done()
            return True
        except Exception as e:
            ghost.fail(e)
            raise
        finally:
            # 任何时间都要解锁.
            ghost.destroy()

    def handle_ghost_event(self, *, ghost: Ghost, event: Event) -> None:
        """
        使用 ghost 实例运行一个事件.
        :param ghost:
        :param event:
        :return:
        """
        # 先按需做初始化.
        ghost.utils().initialize()
        self._handle_ghost_event(ghost=ghost, event=event)

    @staticmethod
    def _handle_ghost_event(ghost: Ghost, event: Event) -> None:
        # 然后才真正运行逻辑.
        op, max_op = ghost.init_operator(event)
        count = 0
        while op is not None:
            if count > max_op:
                # todo: too much operator shall raise an error.
                raise RuntimeError(f"stackoverflow")
            # todo: log op
            _next = op.run(ghost)
            count += 1
            op = _next
        # 结束运行.
        ghost.save()

    @abstractmethod
    def destroy(self) -> None:
        """
        垃圾回收的方法.
        """
        pass

    def shutdown(self) -> None:
        """
        优雅退出的机制.
        """
        shutdown = self.container().get(Shutdown)
        if shutdown is not None:
            shutdown.shutdown()
        self.destroy()
