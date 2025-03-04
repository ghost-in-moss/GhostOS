from __future__ import annotations
from typing import Callable, Type, Optional, TYPE_CHECKING
from abc import ABC
from pydantic import BaseModel
from ghostos_common.helpers import generate_import_path, import_from_path
from ghostos_common.prompter import PromptAbleClass
from ghostos.core.llms import LLMs, LLMApi
from ghostos_moss.utils import make_class_prompt, add_comment_mark
from ghostos_moss.prompts import reflect_code_prompt
from ghostos_moss.pycontext import PyContext
import inspect

if TYPE_CHECKING:
    from ghostos.core.aifunc.interfaces import AIFuncDriver

__all__ = [
    'AIFunc', 'AIFuncResult',
    'get_aifunc_result_type', 'get_aifunc_instruction', 'get_aifunc_pycontext', 'get_aifunc_llmapi',
]


class AIFunc(PromptAbleClass, BaseModel, ABC):
    """
    Model interface for an AIFunc arguments, always followed by an AIFuncResult Model.
    The subclass of AIFunc can run in AIFuncCtx, if you are provided with them, you can use them if you need.
    """

    __aifunc_result__: Optional[Type[AIFuncResult]] = None
    """可以指定自己的 result type, 如果不指定的话, 默认是 cls.__name__ + 'Result' """

    __aifunc_driver__: Optional[Type[AIFuncDriver]] = None
    """可以指定自己的 driver. 不指定的话, 使用系统默认提供的 driver"""

    @classmethod
    def __class_prompt__(cls) -> str:
        if cls is AIFunc:
            source = inspect.getsource(cls)
            return make_class_prompt(source=source, doc=AIFunc.__doc__, attrs=[])
        source = inspect.getsource(cls)
        result_type = cls.__aifunc_result__ if cls.__aifunc_result__ is not None else get_aifunc_result_type(cls)
        result_prompt = reflect_code_prompt(result_type)
        result_prompt = f"result type of {cls.__name__} (which maybe not imported yet) is :\n{result_prompt}"
        return source + "\n\n" + add_comment_mark(result_prompt)

    @classmethod
    def func_name(cls) -> str:
        return generate_import_path(cls)


class AIFuncResult(PromptAbleClass, BaseModel, ABC):
    """
    the AIFuncResult Model
    """

    @classmethod
    def __class_prompt__(cls) -> str:
        source = inspect.getsource(cls)
        if cls is AIFuncResult:
            return make_class_prompt(source=source, doc=AIFunc.__doc__, attrs=[])
        return source


def __aifunc_instruction__(fn: AIFunc) -> str:
    """
    在 AIFunc 的 module 内, 默认需要定义 __aifunc_instruction__ 用于生成智能函数的 llm instruction.
    默认的 Driver 会使用这个方法生成 instruction.
    基于 AIFunc 实例, 生成 System Prompt.
    这个方法是必要的.
    对于 AIFunc 的开发者而言, 必须要感知这个方法.
    对于 AIFunc 的使用者而言, 不一定要直到它怎么实现.
    """
    pass


def __aifunc_llmapi__(fn: AIFunc, llms: LLMs) -> LLMApi:
    """
    定义一个方法返回 LLMs api.
    这个方法可以缺省, 会使用默认的 llms api.
    :param fn:
    :param llms:
    :return:
    """
    pass

# ---- some helpers ---#

def get_aifunc_llmapi(fn: AIFunc, llms: LLMs) -> Optional[LLMApi]:
    """
    默认获取 aifunc llmapi 的逻辑. 用于默认的 Driver.
    :param fn:
    :param llms:
    :return:
    """
    aifunc_cls = fn.__class__
    module = inspect.getmodule(aifunc_cls)
    llmapi_fn = module.__dict__.get('__aifunc_llmapi__', None)
    if llmapi_fn is None:
        return llms.get_api("")
    if not isinstance(llmapi_fn, Callable):
        raise TypeError(f"{module.__name__}  variable __aifunc_llmapi__ is not callable as expected")
    return llmapi_fn(fn, llms)


def get_aifunc_result_type(fn: Type[AIFunc]) -> Type[AIFuncResult]:
    """
    默认获取与 AIFunc 匹配的 AIFuncResult 的方法. 适用于默认的 Driver.
    :param fn:
    :return:
    """
    path = generate_import_path(fn)
    result_path = path + "Result"
    result_type = import_from_path(result_path)
    if not issubclass(result_type, AIFuncResult):
        raise TypeError(f"Type {result_type} does not inherit from QuestResult")
    return result_type


def get_aifunc_pycontext(fn: AIFunc) -> PyContext:
    """
    默认获取 AIFunc 对应的 moss pycontext 的逻辑. 适用于默认的 Driver.
    :param fn:
    :return:
    """
    modulename = fn.__class__.__module__
    return PyContext(
        module=modulename,
    )


def get_aifunc_instruction(fn: AIFunc) -> str:
    """
    默认获取 AIFunc 对应的 instruction 的逻辑. 适用于默认的 Driver.
    :param fn:
    :return:
    """
    aifunc_cls = fn.__class__
    module = inspect.getmodule(aifunc_cls)
    instruction_fn = module.__dict__.get("__aifunc_instruction__", None)
    if instruction_fn is None:
        return None
    if not isinstance(instruction_fn, Callable):
        raise NotImplementedError(f"'__aifunc_instruction__' in {module.__name__} is not Callable as expected.")
    instruction = instruction_fn(fn)
    return str(instruction)

