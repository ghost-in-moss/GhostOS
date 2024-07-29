from typing import List, Optional, Union, AnyStr
from abc import ABC, abstractmethod
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.thoughts import Thought
from ghostiss.core.messages.message import Message, MessageClass

MessageType = Union[Message, MessageClass, AnyStr]


class MultiTasks(ABC):

    @abstractmethod
    def depend_on_tasks(self, *thoughts: Thought) -> Operator:
        """
        使用 Thought 创建多个任务. 然后等待这些任务返回结果, 触发下一轮运行.
        :param thoughts: 每个 Thought 会创建出一个子任务.
        :return:
        """
        pass

    @abstractmethod
    def create_tasks(self, *thoughts: Thought) -> None:
        """
        使用 thoughts 动态创建多个 task.
        :param thoughts:
        """
        pass

    @abstractmethod
    def inform_task(self, name: str, *messages: MessageType) -> None:
        """
        主动向一个指定的 task 进行通讯.
        :param name: task 的名称
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


class Mindflow(ABC):
    """
    这个 library 可以直接管理当前多轮对话里的任务, 通过method 返回的 Operator 会操作系统变更当前任务的状态.
    """

    @abstractmethod
    def send(self, *messages: MessageType) -> None:
        """
        直接发送一条或多条消息.
        """
        pass

    @abstractmethod
    def awaits(self, *questions: MessageType) -> Operator:
        """
        当前任务挂起, 等待下一轮用户输入后重新开始思考.
        如果使用了 MOSS, awaits 是默认的调度方法.
        **当你需要等待用户进一步输入时, 请总是调用这个方法.**
        :param questions: 可以主动向用户提出问题.
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
    def finish(self, *results: MessageType) -> Operator:
        """
        结束当前的任务, 返回任务结果.
        如果当前任务是持续的, 还要等待更多用户输入, 请使用 awaits.
        :param results: 发送一条或多条消息作为任务的结论发送给用户.
        """
        pass

    @abstractmethod
    def fail(self, *reasons: MessageType) -> Operator:
        """
        标记当前任务失败
        :param reasons: 发送一条或多条消息告知用户失败的原因.
        """
        pass
