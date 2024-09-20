from typing import Dict, Any, TypedDict, Required, Optional, Tuple
from abc import ABC, abstractmethod
from ghostos.core.ghosts.operators import Operator
from ghostos.core.ghosts.thoughts import Thought
from ghostos.core.ghosts.assistants import Assistant
from ghostos.core.messages.message import MessageKind
from ghostos.core.llms import ChatPreparer
from dataclasses import dataclass

__all__ = [
    'MultiTask', 'Taskflow', 'Replier',
]


class Taskflow(ABC):
    """
    这个 library 可以直接管理当前任务的状态调度.
    通过method 返回的 Operator 会操作系统变更当前任务的状态.
    """

    @abstractmethod
    def awaits(self, reply: str = "", log: str = "") -> Operator:
        """
        当前任务挂起, 等待下一轮输入.
        :param reply: 可以发送回复, 或者主动提出问题或要求. 并不是必要的.
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
    def think(self, instruction: str = "") -> Operator:
        """
        think another round
        :param instruction: optional instruction for next round thinking
        """
        pass

    @abstractmethod
    def finish(self, log: str, response: str) -> Operator:
        """
        结束当前的任务, 返回任务结果.
        如果当前任务是持续的, 还要等待更多用户输入, 请使用 awaits.
        :param log: 简单记录当前任务完成的理由.
        :param response: 发送一条或多条消息作为任务的结论发送给用户.
        """
        pass

    @abstractmethod
    def fail(self, reason: str, reply: str) -> Operator:
        """
        标记当前任务失败
        :param reason: 记录当前任务失败的原因.
        :param reply: 发送给用户或者父任务的消息. 如果为空的话, 把 log 作为讯息传递.
        """
        pass


class MultiTask(ChatPreparer, ABC):
    """
    You are equipped with this MultiTasks Library that can execute thought in an asynchronous task.
    A thought is a mind-machine usually driven by LLM, can resolve certain type of task in multi-turns chain of thought.
    During the process, the thought may send messages to you, finish/fail the task or await for more information.
    You shall use MultiTasks library to help you resolve your task, interactively and asynchronous.
    """

    @abstractmethod
    def wait_on_tasks(self, *new_tasks: Tuple[str, str, Thought, str]) -> Operator:
        """
        create multiple task by thought, and wait for the tasks to finish.
        when the task finished, you will receive the message and think.
        :param new_tasks: (task_name, task_desc, thought, instruction)
        """
        pass

    @abstractmethod
    def run_tasks(self, *new_tasks: Tuple[str, str, Thought, str]) -> None:
        """
        create
        Cause the tasks are executed asynchronously,
        you can do other things until you got messages that them done.
        :param new_tasks: (task_name, task_desc, thought, instruction)
        """
        pass

    @abstractmethod
    def send_task(self, task_name: str, *messages: str) -> None:
        """
        send a message to the task by name
        :param task_name: task 的名称
        :param messages: the message content
        """
        pass

    @abstractmethod
    def cancel_task(self, task_name: str, reason: str) -> None:
        """
        取消一个已经存在的 task.
        :param task_name: 目标 task 的名称.
        :param reason: 取消的理由.
        """
        pass


# simple and sync version of taskflow
class Replier(ABC):
    """
    reply to the input message
    """

    @abstractmethod
    def reply(self, content: str) -> Operator:
        """
        reply to the input message
        :param content: content of the reply
        :return: wait for further input
        """
        pass

    @abstractmethod
    def finish(self, reply: str) -> Operator:
        """
        finish current task and reply the final result
        :param reply: shall not be empty
        :return: end the current task
        """
        pass

    @abstractmethod
    def ask_clarification(self, question: str) -> Operator:
        """
        the input query is not clear enough, ask clarification.
        :param question: the question will send back
        :return: wait for clarification input
        """
        pass

    @abstractmethod
    def fail(self, reply: str) -> Operator:
        """
        fail to handle request, and reply
        :param reply: content of the reply
        :return: wait for further input
        """
        pass

    @abstractmethod
    def think(
            self,
            observations: Optional[Dict[str, Any]] = None,
            instruction: Optional[str] = None,
    ) -> Operator:
        """
        think another round with printed values or observations
        :param observations: print the observations as message
        :param instruction: tell self what to do next
        :return: think another round
        """
        pass


class MultiAssistant(ABC):

    @abstractmethod
    def ask_assistant(self, assistant: Assistant, query: str) -> None:
        """
        ask an assistant to do something or reply some information.
        :param assistant: the assistant instance
        :param query: query to the assistant.
        """
        pass
