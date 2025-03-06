from typing import List, Union
from ghostos.abcd import Operator
from abc import ABC, abstractmethod


class Planner(ABC):
    """
    a planner that helps you to remember what are you going to do.

    1. you can create task by multi-steps planning
    2. if a task is running, you will receive a message before user input, reminding you what task is going on
    3. you can cancel task any time.
    """

    @abstractmethod
    def save_task(self, name: str, desc: str, steps: List[str]) -> None:
        """
        save a task, if task exists, will reset it.
        :param name: name of the task.
        :param desc: describe the task.
        :param steps:  the step description in nature language.
        """
        pass

    @abstractmethod
    def next(self, task_name: Union[str, None] = None, *, wait: bool = False) -> Operator:
        """
        go to next step of the task.
        :param task_name: task name that work on.  if None, choose current task.
        :param wait: if True, wait for user input. otherwise you will think for next step.
        :return: mindflow Operator
        """
        pass

    @abstractmethod
    def cancel(self, task_name: Union[str, None] = None) -> Operator:
        """
        cancel task.
        :param task_name: if None, cancel current task
        :return: mindflow Operator
        """
        pass
