from typing import Optional, Callable, Tuple
from abc import ABC, abstractmethod
from ghostiss.entity import EntityMeta
from ghostiss.core.messages import Stream
from ghostiss.core.session import Session, EventBus, Event, Tasks, Task
from ghostiss.core.ghosts import Ghost, Inputs
from ghostiss.contracts.logger import LoggerItf
from ghostiss.container import Container
from ghostiss.helpers import uuid, Timeleft


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
    def find_session(
            self, *,
            upstream: Stream,
            task_id: str,
            task: Optional[Task] = None,
    ) -> Optional[Session]:
        """
        找到一个判断已经存在的 Session
        :param upstream:
        :param task_id:
        :param task: exists task.
        :return:
        """
        pass

    @abstractmethod
    def create_session(
            self, *,
            ghost_meta: EntityMeta,
            upstream: Stream,
            session_id: str,
            is_async: bool,
            task_id: Optional[str] = None,
    ) -> Session:
        """
        根据请求, 实例化 Session. 一切功能的起点.
        :param ghost_meta: 基于 ghost_meta 配置项生成 Session. ghost_meta 主要用来生成进程.
        :param upstream: 上游的消息通道. 接收方应该于外部定义. 对于异步运行的 Session,
                         上游的 upstream 应该不发送消息到端, 除非支持多流协议.
        :param session_id: 必填.
        :param is_async: 如果 is_async 为 True, ghost 的所有任务包括子任务都只能 background 运行.
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
    def tasks(self) -> Tasks:
        pass

    def instance_ghost(self, session: Session) -> Ghost:
        """
        使用 Session 实例化当前的 Ghost.
        """
        pass

    def on_inputs(self, inputs: Inputs, upstream: Stream, is_async: bool = False) -> Optional[Callable[[], bool]]:
        """
        处理同步请求. deliver 的实现应该在外部.
        这个方法是否异步执行, 也交给外部判断.
        :param inputs: 同步请求的参数.
        :param upstream: 对上游输出的 output
        :param is_async: 是否异步运行.
        :returns: 返回一个闭包, 执行它会真正运转 ghost. 直到它的返回值为 false.
        """
        if not inputs.trace:
            inputs.trace = uuid()
        task_id = inputs.task_id if inputs.task_id else inputs.trace
        session_id = inputs.session_id
        session = self.find_session(upstream=upstream, task_id=task_id)
        if session is None:
            session = self.create_session(
                ghost_meta=inputs.ghost_meta,
                upstream=upstream,
                session_id=session_id,
                task_id=task_id,
                is_async=is_async,
            )
        ghost = self.instance_ghost(session)
        err = None
        try:
            # 处理 input.
            event = ghost.on_inputs(inputs)
            # todo: 异常体系以后管理.
            if event is None:
                # 无锁操作, 拦截事件.
                return None

            eventbus = self.eventbus()
            # 发送事件.
            eventbus.send_event(event, notify=is_async)
            task_id = session.task().task_id

            # 尝试运行一轮, 但是要加锁.
            def main() -> bool:
                # 每一轮要实例化一个新的 session.
                running_session = self.find_session(upstream=upstream, task_id=task_id)
                if running_session is None:
                    # 为 None 通常是没有锁上.
                    return False
                return self.background_run_session_event(running_session, task_id=task_id)

            ghost.finish()
            session.finish()
            return main

        except Exception as e:
            err = e
            raise
        finally:
            # 主 session 只是为了完成初始化创建, 还有拦截消息.
            if err is not None:
                ghost.fail(err)
                session.fail(err)
            ghost.destroy()
            session.destroy()

    def background_run(self, upstream: Stream, timeout: float = 0.0) -> bool:
        """
        尝试从 EventBus 中获取一个 task 的信号, 并运行它.
        :param upstream:
        :param timeout:
        :return:
        """
        try:
            timeleft = Timeleft(timeout)
            handled = False
            while timeleft.left() > 0:
                # 暂时不传递 timeout.
                handled = self.background_run_task_notification(upstream)
                if handled:
                    # 只执行一次任务. 如果没有 handled, 就尝试继续运行别的 task_notification.
                    break
            return handled
        finally:
            pass

    def background_run_task_notification(self, upstream: Stream) -> Tuple[bool, bool, bool]:
        """
        尝试从 eventbus 里 pop 一个事件, 然后运行.
        外部系统应该管理所有资源分配, 超时的逻辑.
        下一层方法是: self.background_run_task_events()
        :return: (notified, locked, handled)
        :exception: todo
        """
        notified = False
        handled = False
        locked = False
        eventbus = self.eventbus()
        logger = self.logger()
        task_id = eventbus.pop_task_notification()
        # 没有读取到任何全局任务.
        if task_id is None:
            logger.info("no background task was found")
            return notified, locked, handled
        notified = True
        locked, handled = self.background_lock_task_run_event(upstream=upstream, task_id=task_id)
        return notified, locked, handled

    def background_lock_task_run_event(
            self, *,
            upstream: Stream,
            task_id: str,
    ) -> Tuple[bool, bool]:
        """
        指定一个 task id, 尝试运行它的事件.
        下一层方法是: self.background_run_session_event()
        :param upstream:
        :param task_id: 指定的 task id
        :return: (locked, handled)
        """
        handled = False
        logger = self.logger()
        tasks = self.tasks()
        task = tasks.get_task(task_id, lock=True)
        lock = task.lock
        locked = lock is not None
        # task 没有抢到锁.
        if not locked:
            return locked, handled

        try:
            # 先创建 session.
            session = self.find_session(upstream=upstream, task_id=task_id, task=task)
            if session is None:
                logger.error(f"no session was found by task_id: {task_id}")
                return locked, handled
            handled = self.background_run_session_event(session, task_id=task_id)
            return locked, handled

        finally:
            # 任何时间都要解锁.
            tasks.unlock_task(task_id, lock)

    def background_run_session_event(self, session: Session, task_id: str) -> bool:
        """
        实例化 Session 后再 pop task event.
        下一层方法是: self.handle_ghost_event
        :param session:
        :param task_id:
        :return: 如果没有任何任务需要继续处理了, 返回 False.
        """
        err = None
        shall_continue_to_notify = True
        eventbus = self.eventbus()
        try:
            popped = eventbus.pop_task_event(task_id=task_id)
            if popped is None:
                # 没有任何事件, 就不需要再继续推骨牌了.
                shall_continue_to_notify = False
                return False
            # 无论怎么样都运行.
            ghost = self.instance_ghost(session)
            self.handle_ghost_event(ghost=ghost, event=popped)

            # session finish 在 ghost 之后.
            session.finish()
            return True
        except Exception as exp:
            # 异常都应该被 ghost 处理. 否则应该向上反馈.
            err = exp
            # todo: eventbus 通知父任务系统异常失败.
            raise
        finally:
            # 如果不能确定 task 等待事件为空, 就需要传递一个信号, 继续消费 notification.
            if shall_continue_to_notify:
                eventbus.notify_task(task_id=task_id)

            # 清空 session.
            if err is not None:
                session.fail(err)
            session.destroy()

    @abstractmethod
    def handle_ghost_event(self, *, ghost: Ghost, event: Event) -> None:
        """
        使用 ghost 实例运行一个事件.
        :param ghost:
        :param event:
        :return:
        """
        err = None
        # 先按需做初始化.
        on_created = ghost.utils().initialize()
        if on_created is not None:
            self.handle_ghost_event(ghost=ghost, event=on_created)

        # 然后才真正运行逻辑.
        try:
            op, max_op = ghost.init_operator(event)
            count = 0
            session = ghost.session()
            while op is not None:
                if count > max_op:
                    # todo: too much operator shall raise an error.
                    raise RuntimeError(f"stackoverflow")
                # todo: log op
                _next = op.run(ghost)
                # 检查 session 状态.
                if not (session.alive() and session.refresh_lock()):
                    raise RuntimeError(f"session is overdue")
                count += 1
                op = _next
            # 结束运行.
            ghost.finish()
        except Exception as exp:
            err = exp
        finally:
            if err is not None:
                ghost.fail(err)
            ghost.destroy()
