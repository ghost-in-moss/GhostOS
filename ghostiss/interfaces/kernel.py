from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Tuple, List, Union
from ghostiss.context import Context
from ghostiss.messages import Messenger, Message
from ghostiss.meta import MetaData
from ghostiss.interfaces.thoughts import Thought, Event, OnTaskCreation, OnIntercept
from ghostiss.interfaces.runtime import Runtime, Process, Task, NewTask, TaskState
from ghostiss.interfaces.threads import Threads, ThreadRun, Inputs, Turn
from ghostiss.interfaces.helpers import Helper

if TYPE_CHECKING:
    from ghostiss.interfaces.agent import Agent, Matrix
    from ghostiss.interfaces.llms import LLMs


class Operator(ABC):
    """
    操作 kernel 的算子.
    """

    @abstractmethod
    def run(self, ctx: "Context", agent: "Agent", kernel: "Kernel") -> Optional["Operator"]:
        pass


class Kernel(ABC):
    llms: "LLMs"
    matrix: "Matrix"
    threads: "Threads"
    runtime: "Runtime"
    helper: "Helper"

    def run_operator(self, ctx: "Context", agent: "Agent", op: Operator) -> None:
        """
        运行一个算子多米诺.
        """
        next_op: Optional[Operator] = op
        while next_op is not None:
            with ctx:
                # todo: 日志.
                next_op = op.run(ctx, agent, self)

    def think(
            self,
            ctx: "Context",
            agent: "Agent",
            thought_data: Union[MetaData, Thought],
            thread_run: "ThreadRun",
    ) -> Tuple[List[Message], Optional[Operator]]:
        """
        运行思考逻辑. 是无锁的.
        """
        with ctx:
            if isinstance(thought_data, Thought):
                thought = thought_data
            else:
                thinker = agent.ghost.mindset().force_fetch(ctx, thought_data.clazz)
                thought = thinker.meta_new(thought_data)

            # make messenger
            messenger = thinker.messenger(ctx, thought, agent)

            # generate llm run
            llm_run = thinker.generate_run(ctx, thought, agent, thread_run)

            # run llm
            self.llms.run(ctx, llm_run, messenger)
            # notice: update thread from outside
            outputs = messenger.wait()

            # attention handling
            attentions = thinker.attentions(ctx, thought)
            for attention in attentions:
                op = attention.attend(outputs)
            if op is None:
                op = thinker.fallback(ctx, thought, agent, thread_run)
            return outputs, op

    def run_async_agents(self, ctx: Context) -> bool:
        """
        异步运行的基本逻辑.
        """
        inputs = self.runtime.pop_threads_inputs()
        if inputs is None:
            return False
        if not inputs.task_id:
            # todo: log
            return False

        task = self.runtime.get_task(ctx, inputs.task_id, True)
        # 没有锁到 task.
        if task is None:
            # 预计 task 自己会将消息处理完.
            # 将 thread inputs 输入给 task inputs.
            self.runtime.push_task_inputs(ctx, inputs.task_id, inputs)
            return False

        # 抢到锁了, 正常运行逻辑.
        process = self.runtime.get_process(ctx, task.process_id)
        if process is None:
            # todo: Log
            return False
        agent = self.matrix.forge(process.source_code)
        self.run_task(ctx, agent, task, inputs)
        return True

    def fire_task_event(self, ctx: "Context", agent: "Agent", event: "Event") -> Tuple[Task, bool]:
        """
        处理 task event. 不需要加锁.
        """
        with ctx:
            thinker = agent.ghost.mindset().force_fetch(ctx, event.task.thought.clazz)
            thought = thinker.meta_new(event.task.thought)
            # 运行 event.
            op = thinker.on_event(ctx, thought, agent, event)
            if op is not None:
                self.run_operator(ctx, agent, op)
                if event.task.is_locked():
                    # 重新取出 task.
                    task = self.runtime.get_task(ctx, event.task.task_id, False)
                    task.locker = event.task.locker
                    return task, True
            return event.task, False

    def callback_tasks(self, ctx: "Context", from_task: str, turn: Turn, *task_ids: str) -> None:
        """
        将消息回调给若干 task.
        """
        if not task_ids:
            return None

        broadcast_threads = set()
        for task_id in task_ids:
            # 必须要加锁成功.
            callback_task = self.runtime.get_task(ctx, task_id, True)
            if callback_task is None:
                continue
            if callback_task.state != TaskState.DEPENDING:
                continue
            if from_task not in callback_task.callbacks:
                continue
            # 更新 task 的 callback
            callbacks = set(callback_task.callbacks)
            callbacks.remove(from_task)
            callback_task.callbacks = list(callbacks)
            # 更新目标 task 的状态.
            if not callback_task.callbacks:
                callback_task.state = TaskState.QUEUED
            # 更新 callback task 的状态.
            self.runtime.update_task(ctx, callback_task)

        # 如果需要广播到这些 thread.
        if broadcast_threads:
            # 广播消息. 到最新的一回合 run 中.
            self.threads.append_turn(ctx, list(broadcast_threads), turn)

    def run_task(self, ctx: "Context", agent: "Agent", task: "Task", inputs: "Inputs", more: int = 1) -> None:
        """
        运行一个 task.
        """
        locked = False
        with ctx:
            # 是否拦截.
            intercept = OnIntercept(task, inputs)
            task, intercepted = self.fire_task_event(ctx, agent, intercept)
            if intercepted:
                # 被拦截了就不要返回.
                return

            # 拦截失败需要抢锁. task 如果不是 waiting 状态, 也不能接受新消息.
            if task.state != TaskState.WAITING:
                locked = self.lock_task(ctx, task)
                if not locked:
                    # 没有抢到 task 的锁.
                    overflow = self.runtime.push_task_inputs(ctx, inputs.task_id, inputs)
                    # 执行 overflow 的信息.
                    if overflow is not None:
                        task, _ = self.fire_task_event(ctx, agent, overflow)
                    return None

            # 更新 task 的状态.
            task.state = TaskState.RUNNING
            self.runtime.update_task(ctx, task)

            # 更新 locker.
            # 运行.
            try:
                thread = self.threads.get_thread(ctx, task.thread_id)
                if thread is None:
                    thread = self.threads.create_thread(ctx, task.thread_id, inputs.context)

                run = self.threads.get_run(ctx, thread, inputs)
                outputs, op = self.think(ctx, agent, task.thought, run)

                # 状态更新.
                turn = self.threads.update_run(ctx, run, outputs)
                # 执行必要的回调.
                if task.callbacks:
                    self.callback_tasks(ctx, task.task_id, turn, *task.callbacks)

                # 运行 op
                if op is not None:
                    # todo: default op ?
                    self.run_operator(ctx, agent, op)

            except Exception as e:
                ctx.fail(e)
            finally:
                # 必须要解锁.
                if locked:
                    self.runtime.unlock_task(ctx, task.task_id, task.locker)
        more = more - 1
        # 不继续拉取了.
        if not more:
            return None

        #  继续 pop
        with ctx:
            # 继续处理输入.
            inputs = self.runtime.pop_task_inputs(ctx, task)
            if inputs is not None:
                # 尾调用继续消费历史消息. 不通过 op 来操作.
                return self.run_task(ctx, agent, task, inputs, more)
            # 继续处理 queued.
            popped = self.runtime.pop_thread_queued_task(task.thread_id)
            if popped is not None:
                queued_run_inputs = Inputs.new_queued_run(popped.task_id)
                return self.run_task(ctx, agent, popped, queued_run_inputs, more)
        return None

    def run_agent(self, ctx: "Context", agent: "Agent", inputs: "Inputs") -> None:
        """
        """
        with ctx:
            process = self.runtime.get_process(ctx, agent.id())
            # 没有独立的进程.
            if process is None:
                process = self.runtime.create_process(ctx, agent.get_meta().to_meta_data())

            task = self.runtime.get_task(ctx, process.process_id, True)
            # 完成整个 process 的初始化.
            if task is None:
                new_task = NewTask(
                    process_id=process.process_id,
                    thread_id=process.process_id,
                    thought=agent.ghost.root_thought(),
                )
                # 创建 task. 理论上要自带锁.
                task = self.runtime.create_task(ctx, new_task)
                # 执行 task 的初始化逻辑.
                event = OnTaskCreation(task)
                task, _ = self.fire_task_event(ctx, agent, event)

            # run task
            self.run_task(ctx, agent, task, inputs)

    def create_task(self, ctx: "Context", agent: "Agent", new_task: NewTask) -> Task:
        """
        创建 Task
        """
        task = self.runtime.create_task(ctx, new_task)
        event = OnTaskCreation(task)
        task, _ = self.fire_task_event(ctx, agent, event)
        return task

    def lock_task(self, ctx: "Context", task: "Task") -> bool:
        """
        task 是整个系统里唯一带锁的. 所以必须执行锁.
        """
        # task 已经锁了.
        if task.locker:
            return True

        locker = self.runtime.lock_task(ctx, task.task_id)
        if locker:
            task.locker = locker
            return True
        return False
