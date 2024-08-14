from typing import Union, AnyStr, Dict
from abc import ABC, abstractmethod
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.thoughts import Thought
from ghostiss.core.messages.message import Message, MessageClass

MessageType = Union[Message, MessageClass, AnyStr]


class MultiTask(ABC):
    """
    You are equipped with this MultiTasks Library that can execute thought in an asynchronous task.
    A thought is a mind-machine usually driven by LLM, can resolve certain type of task in multi-turns chain of thought.
    During the process, the thought may send messages to you, finish/fail the task or await for more information.
    You shall use MultiTasks library to help you resolve your task, interactively and asynchronous.
    """

    @abstractmethod
    def wait_on_tasks(self, *thoughts: Thought) -> Operator:
        """
        使用 Thought 创建多个任务, 同时等待这些任务返回结果. 当结果返回时会触发下一轮思考.
        :param thoughts: 每个 Thought 会创建出一个子任务.
        """
        pass

    @abstractmethod
    def run_tasks(self, *thoughts: Thought) -> Dict[str, str]:
        """
        使用 thoughts 动态创建多个 task 异步运行. 不影响你当前状态.
        :return: dict of created task name to description
        """
        pass

    @abstractmethod
    def send_task(self, task_name: str, *messages: MessageType) -> None:
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


class Taskflow(ABC):
    """
    这个 library 可以直接管理当前任务的状态调度.
    通过method 返回的 Operator 会操作系统变更当前任务的状态.
    """

    @abstractmethod
    def send(self, *messages: MessageType) -> None:
        """
        直接发送一条或多条消息.
        """
        pass

    @abstractmethod
    def awaits(self, *replies: MessageType, log: str = "") -> Operator:
        """
        当前任务挂起, 等待下一轮输入.
        :param replies: 可以发送回复, 或者主动提出问题或要求. 并不是必要的.
        :param log: 如果不为空, 会更新当前任务的日志. 只需要记录对任务进行有意义而且非常简介的讯息.
        """
        pass

    @abstractmethod
    def observe(self, *args, **kwargs) -> Operator:
        """
        系统会打印这些变量的值, 作为一条新的输入消息让你观察, 开启你的下一轮思考.
        是实现 Chain of thought 的基本方法.
        """
        pass

    @abstractmethod
    def finish(self, log: str, *response: MessageType) -> Operator:
        """
        结束当前的任务, 返回任务结果.
        如果当前任务是持续的, 还要等待更多用户输入, 请使用 awaits.
        :param log: 简单记录当前任务完成的理由.
        :param response: 发送一条或多条消息作为任务的结论发送给用户.
        """
        pass

    @abstractmethod
    def fail(self, log: str, *messages: MessageType) -> Operator:
        """
        标记当前任务失败
        :param log: 记录当前任务失败的原因.
        :param messages: 发送给用户或者父任务的消息. 如果为空的话, 把 log 作为讯息传递.
        """
        pass
