from __future__ import annotations
from abc import ABC
from typing import Iterable, Dict, Any, Callable, Optional
from ghostos.core.ghosts import ModelThought, Operator
from ghostos.thoughts.basic import LLMThoughtDriver
from ghostos.thoughts.moss_thought import BasicMossThoughtDriver
from ghostos.core.moss import PyContext, MossCompiler
from ghostos.core.ghosts import Ghost, Action
from ghostos.core.llms import LLMApi
from ghostos.core.runtime import Event, Session, GoThreadInfo
from ghostos.container import Provider
import inspect
from pydantic import Field

__all__ = ["MagicMossThought"]

"""
this file 
"""


class MagicMossThought(ModelThought, ABC):
    """
    Magic Moss Thought is a sub Thought class that can be extended at any module,
    The subclass of MagicMossThought will take the module it located as the moss file which provides libs to it.
    """
    debug: bool = Field(default=False, description="if the debug mode is on")


# <moss-hide>

def __magic_moss_thought_instruction__(thought: MagicMossThought, g: "Ghost", e: "Event") -> str:
    """
    generate instruction, this method is not optional
    :param thought:
    :param g:
    :param e:
    :return: instruction to the llm
    """
    return ""


def __magic_moss_thought_llmapi__(thought: MagicMossThought, g: "Ghost") -> "LLMApi":
    """
    optional magic function that define the thought's llmapi
    """
    return g.llms().get_api("")


def __magic_moss_thought_providers__(thought: MagicMossThought) -> Iterable["Provider"]:
    """
    optional magic function that define the thought's providers, register in moss compiler
    """
    return []


def __magic_moss_thought_injections__(thought: MagicMossThought) -> "Dict[str, Any]":
    """
    optional magic function that define the thought's injections, inject into moss instance
    """
    return {}


def __magic_moss_thought_actions__(thought: MagicMossThought, g: "Ghost", e: "Event") -> Iterable["Action"]:
    """
    optional magic function that define the thought's actions
    """
    return {}


def __magic_moss_thought_compiling__(thought: MagicMossThought, g: "Ghost", compiler: "MossCompiler") -> "MossCompiler":
    """
    optional magic function that prepare a moss compiler by inject / bind / register implementations.
    :param thought:
    :param g:
    :param compiler:
    :return:
    """
    return compiler


def __magic_moss_thought_thread__(thought: MagicMossThought, session: Session, thread: GoThreadInfo) -> GoThreadInfo:
    """
    optional magic function that prepare the thread info, such as modify thread.save_file
    :param thought:
    :param session:
    :param thread:
    """
    return thread


def __on_inputs__(driver: MagicMossThoughtDriver, g: Ghost, e: Event) -> Optional[Operator]:
    """
    example to custom event handler of the thought. if exists, will replace the default handler.
    :param driver:
    :param g:
    :param e:
    :return:
    """
    pass


# </moss-hide>

class MagicMossThoughtDriver(LLMThoughtDriver[MagicMossThought], BasicMossThoughtDriver):

    def __init__(self, thought: MagicMossThought):
        super().__init__(thought)
        self._moss_module = inspect.getmodule(thought)

    def on_event(self, g: Ghost, e: Event) -> Optional[Operator]:
        name = e.type
        # can use magic method to intercept default event handling.
        method = "__on_" + name + "__"
        fn = self.get_magic_func_of_the_module(method)
        if fn is not None:
            return fn(self, g, e)
        return super().on_event(g, e)

    def providers(self) -> Iterable[Provider]:
        fn = self.get_magic_func_of_the_module(__magic_moss_thought_providers__.__name__)
        if fn is None:
            fn = __magic_moss_thought_providers__
        return fn(self.thought)

    def injections(self) -> Dict[str, Any]:
        fn = self.get_magic_func_of_the_module(__magic_moss_thought_injections__.__name__)
        if fn is None:
            fn = __magic_moss_thought_injections__
        return fn(self.thought)

    def prepare_moss_compiler(self, g: Ghost, compiler: MossCompiler) -> MossCompiler:
        fn = self.get_magic_func_of_the_module(__magic_moss_thought_compiling__.__name__)
        if fn is None:
            fn = __magic_moss_thought_compiling__
        return fn(self.thought, g, compiler)

    def prepare_thread(self, session: Session, thread: GoThreadInfo) -> GoThreadInfo:
        thread = super().prepare_thread(session, thread)
        fn = self.get_magic_func_of_the_module(__magic_moss_thought_thread__.__name__)
        if fn is None:
            fn = __magic_moss_thought_thread__
        return fn(self.thought, session, thread)

    def get_magic_func_of_the_module(self, func_name: str) -> Optional[Callable]:
        module = self._moss_module
        if func_name in module.__dict__:
            return module.__dict__[func_name]
        return None

    def get_llmapi(self, g: Ghost) -> "LLMApi":
        fn = self.get_magic_func_of_the_module(__magic_moss_thought_llmapi__.__name__)
        if fn is None:
            fn = __magic_moss_thought_llmapi__
        return fn(self.thought, g)

    def actions(self, g: Ghost, e: Event) -> Iterable["Action"]:
        yield from BasicMossThoughtDriver.actions(self, g, e)
        fn = self.get_magic_func_of_the_module(__magic_moss_thought_actions__.__name__)
        if fn is None:
            fn = __magic_moss_thought_actions__
        yield from fn(self.thought, g, e)

    def instruction(self, g: Ghost, e: Event) -> str:
        fn = self.get_magic_func_of_the_module(__magic_moss_thought_instruction__.__name__)
        if fn is None:
            fn = __magic_moss_thought_instruction__
        return fn(self.thought, g, e)

    def init_pycontext(self) -> PyContext:
        module = self._moss_module
        return PyContext(
            module=module.__name__,
        )

    def is_moss_code_delivery(self) -> bool:
        return self.thought.debug


MagicMossThought.__thought_driver__ = MagicMossThoughtDriver
