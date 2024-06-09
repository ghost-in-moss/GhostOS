from abc import ABC, abstractmethod
from typing import List, Callable
from pydantic import BaseModel
import datetime


class Future(BaseModel):
    """
    一个可以观测的结果.
    """
    id: str
    name: str
    descr: str


def get_weather(city: str, date: datetime.date) -> Future:
    """
    获取一个城市的天气.
    """
    pass


class Thought(ABC):
    """
    你思维的控制器.
    """

    @abstractmethod
    def observe(self, **values) -> None:
        """
        观测上下文中产生的值.
        """
        pass

    @abstractmethod
    def async_call(self, name: str, desc: str, caller: Callable, *args, **kwargs) -> Future:
        """
        异步调用一个函数, 得到一个可观测的结果.
        """
        pass

    @abstractmethod
    def awaits(self, future: Future, instructions: str, on_err: str) -> None:
        """
        观测一个 future 的结果.
        instructions: 用自然语言记录拿到结果后应该怎么做
        on_err: 用自然语言记录如果出错了应该怎么做.
        """
        pass

    @abstractmethod
    def awaits_all(self, future: List[Future], instructions: str, on_err: str) -> None:
        """
        等多个 future 实现后, 一起观测.
        """
        pass

    @abstractmethod
    def awaits_race(self, futures: List[Future], instructions: str, on_err: str) -> None:
        """
        观测若干个 future 中第一个返回的结果.
        """
        pass

    @abstractmethod
    def restart(self, logs: str) -> None:
        """
        从头开始思考问题. 记录日志, 方便未来思考.
        """
        pass


