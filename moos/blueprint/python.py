from typing import Any, Dict, Iterator
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class Variable(BaseModel):
    """
    Variable that can be used in python runtime
    """

    desc: str = Field(description="description of the variable")
    wrapper: str = Field(default="", description="if wrapper exists, use wrapper(data) to get variable instance")
    codes: str = Field(description="codes of the variable, if wrapper not exits, use codes to wrapper data")
    data: Any = Field(default=None, description="data of the variable")


class PythonOS(ABC):

    @abstractmethod
    def import_module(self, name: str) -> None:
        pass


class PythonContext(ABC):
    """
    the context of the python runtime for llm-based agent

    Context 需要包含所有对 LLM 可见的 代码和工具.
    用于构建对话上下文, 并且支持被调用.
    """

    @abstractmethod
    def runtime_codes(self) -> str:
        """
        生成 python runtime 依赖的代码, 会输出到代码的上文里.
        """
        pass

    @abstractmethod
    def runtime_vars(self) -> Dict[str, Any]:
        """
        输出 python runtime 可以调用的上下文变量.
        可能用 exec 去执行代码.
        """
        pass

    @abstractmethod
    def os(self) -> PythonOS:
        pass


class PythonInterpreter(ABC):
    """
    为 Kernel 实现的解释器, 可以理解上下文, 并且运行代码.
    考虑初期只支持 Python.
    脚本语言有优势.
    """

    @abstractmethod
    def run(self, ctx: PythonContext, source: str) -> None:
        """
        同步运行一段 python 代码. 会同步操作 PythonContext
        异步逻辑应该在 run 的外部, 传递给 run 的是一个异步 os.
        """
        pass
