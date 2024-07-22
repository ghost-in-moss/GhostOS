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


class TaskManager(ABC):
    """

    """

    @abstractmethod
    def fork(self, *quests: Optional[MessageType]) -> Operator:
        """
        fork 当前的会话, 运行子任务.
        :param quests:
        """
        pass

    @abstractmethod
    def ask(self, *messages: MessageType) -> Operator:
        """
        向上一层提出问题.
        :param messages:
        :return:
        """
        pass

    @abstractmethod
    def finish(self, *messages: MessageType) -> Operator:
        """
        结束当前任务, 对当前任务进行总结.
        :param messages:
        :return:
        """
        pass

    @abstractmethod
    def fail(self, *reasons: MessageType) -> Operator:
        """
        标记当前任务失败, 和失败的原因.
        """
        pass
