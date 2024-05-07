from __future__ import annotations

from abc import ABC, abstractmethod
from .container import Container

INSTRUCTION = """
面向内核开发者看到的 Kernel 实现. 


"""


class Kernel(ABC):
    """
    系统内核.
    """

    # kernel 的基本属性.

    @property
    @abstractmethod
    def container(self) -> Container:
        """
        获取全局的 IoC 容器.
        """
        pass

    @property
    @abstractmethod
    def runtime(self) -> Runtime:
        """
        获取系统的 Runtime, 管理相关的 API.
        """
        pass

    @property
    @abstractmethod
    def python(self) -> PythonInterpreter:
        pass

    # 运行代码.

    def run(self, initial_operator: Operator) -> None:
        """
        驱动所有的 Operators, 循环运行. 
        """
        pass


# system runtime .

class Runtime(ABC):
    """
    通过 Runtime 对象管理进程的资源和相关 API 的调用.
    """


class Process(ABC):
    """
    系统运行的进程.
    """


class Thread(ABC):
    """
    系统运行的独立资源. 暂时不发明新的概念.
    资源里包含多种数据的汇聚:
    1. 对话历史
    2. 思考历史
    3. 代码运行历史

    未来 Thread 是一个需要独立保存的重要资源.
    """


class Operator(ABC):
    """
    运行时用来操作底层系统运转的算子.
    算子可以持有当前运行状态, 用来操作 Kernel.
    算子本身可以构成复杂的同步逻辑链条, 但不适合解决异步问题.
    s
    """

    @abstractmethod
    def run(self, kernel: Kernel) -> Operator | None:
        """
        运行一个底层的算子, 用来驱动一个状态机链条.
        """
        pass

