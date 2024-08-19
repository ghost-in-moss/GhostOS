from typing import Dict, Any
from abc import ABC, abstractmethod
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.thoughts import Thought
from ghostiss.core.messages.message import MessageKind

__all__ = [
    'MultiTask', 'Taskflow',
]


class Taskflow(ABC):
    """
    这个 library 可以直接管理当前任务的状态调度.
    通过method 返回的 Operator 会操作系统变更当前任务的状态.
    """

    @abstractmethod
    def awaits(self, *replies: MessageKind, log: str = "") -> Operator:
        """
        当前任务挂起, 等待下一轮输入.
        :param replies: 可以发送回复, 或者主动提出问题或要求. 并不是必要的.
        :param log: 如果不为空, 会更新当前任务的日志. 只需要记录对任务进行有意义而且非常简介的讯息.
        """
        pass

    @abstractmethod
    def observe(self, objects: Dict[str, Any], reason: str = "", instruction: str = "") -> Operator:
        """
        系统会打印这些变量的值, 作为一条新的输入消息让你观察, 开启你的下一轮思考.
        是实现 Chain of thought 的基本方法.
        :param objects: the observing objects by name to value
        :param reason: if given, will record the observing reason to task logs.
        :param instruction: give the instruction when observe the result, in case of forgetting.
        """
        pass

    @abstractmethod
    def finish(self, log: str, *response: MessageKind) -> Operator:
        """
        结束当前的任务, 返回任务结果.
        如果当前任务是持续的, 还要等待更多用户输入, 请使用 awaits.
        :param log: 简单记录当前任务完成的理由.
        :param response: 发送一条或多条消息作为任务的结论发送给用户.
        """
        pass

    @abstractmethod
    def fail(self, reason: str, *messages: MessageKind) -> Operator:
        """
        标记当前任务失败
        :param reason: 记录当前任务失败的原因.
        :param messages: 发送给用户或者父任务的消息. 如果为空的话, 把 log 作为讯息传递.
        """
        pass


class MultiTask(ABC):
    """
    You are equipped with this MultiTasks Library that can execute thought in an asynchronous task.
    A thought is a mind-machine usually driven by LLM, can resolve certain type of task in multi-turns chain of thought.
    During the process, the thought may send messages to you, finish/fail the task or await for more information.
    You shall use MultiTasks library to help you resolve your task, interactively and asynchronous.
    """

    @abstractmethod
    def wait_on_tasks(self, *thoughts: Thought, reason: str = "", instruction: str = "") -> Operator:
        """
        使用 Thought 创建多个任务, 同时等待这些任务返回结果. 当结果返回时会触发下一轮思考.
        :param thoughts: 每个 Thought 会创建出一个子任务.
        :param reason: if given, will log why create the tasks to the current task.
        :param instruction: if given, will notice the instruction for you when receive callback from the tasks.
        """
        pass

    @abstractmethod
    def run_tasks(self, *thoughts: Thought) -> None:
        """
        使用 thoughts 动态创建一个或者多个 task 异步运行. 不影响你当前状态.
        """
        pass

    @abstractmethod
    def send_task(self, task_name: str, *messages: MessageKind) -> None:
        """
        主动向一个指定的 task 进行通讯.
        :param task_name: task 的名称
        :param messages: 消息会发送给目标 task
        """
        pass

    @abstractmethod
    def cancel_task(self, name: str, reason: str) -> None:
        """
        取消一个已经存在的 task.
        :param name: 目标 task 的名称.
        :param reason: 取消的理由.
        """
        pass
