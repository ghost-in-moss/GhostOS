from typing import Optional, List
from ghostos_container import Container, Provider
from ghostos_moss.abcd import (
    Moss, MossCompiler, MossRuntime, MossPrompter, Execution,
    AttrPrompts, Injection,
    MOSS_VALUE_NAME, MOSS_TYPE_NAME, MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
)
from ghostos_moss.modules import Modules, ImportWrapper, DefaultModules, DefaultModulesProvider
from ghostos_moss.moss_impl import DefaultMOSSProvider
from ghostos_moss.testsuite import MossTestSuite
from ghostos_moss.pycontext import PyContext
from ghostos_moss.exports import Exporter
from ghostos_moss.magics import __is_subclass__, __is_instance__, MagicPrompter
from ghostos_moss.prompts import PromptAbleClass, PromptAbleObj
from contextlib import contextmanager

__all__ = [
    # abstract contracts
    'Moss', 'MossCompiler', 'MossRuntime', 'MossPrompter', 'Execution',
    # constants
    'MOSS_VALUE_NAME', 'MOSS_TYPE_NAME', 'MOSS_HIDDEN_MARK', 'MOSS_HIDDEN_UNMARK',
    # types
    'AttrPrompts',
    # pycontext related
    'PyContext',
    # testing
    'DefaultMOSSProvider',
    'MossTestSuite',

    'Exporter',  # useful to exports values in group, and other module will reflect them in moss_imported_attrs_prompt
    'moss_container',
    'moss_test_suite',

    # magic prompters
    '__is_subclass__',
    '__is_instance__',
    'MagicPrompter',

    'PromptAbleClass', 'PromptAbleObj',

    'get_moss_compiler', 'moss_runtime_ctx',
]


def moss_container() -> Container:
    """
    test container for Moss
    """
    from ghostos_moss.modules import DefaultModulesProvider
    container = Container()
    container.register(DefaultMOSSProvider())
    return container


def get_moss_compiler(container: Optional[Container] = None) -> MossCompiler:
    """
    get moss compiler from container or make one.
    """
    if container is None:
        container = moss_container()
    return container.force_fetch(MossCompiler)


@contextmanager
def moss_runtime_ctx(
        modulename: str,
        *,
        container: Optional[Container] = None,
        providers: Optional[List[Provider]] = None,
        pycontext: Optional[PyContext] = None,
) -> MossRuntime:
    compiler = get_moss_compiler(container)
    if pycontext is not None:
        compiler = compiler.join_context(pycontext)
    if providers is not None:
        for provider in providers:
            compiler.register(provider)
    with compiler:
        runtime = compiler.compile(modulename)
        with runtime:
            yield runtime


def moss_test_suite() -> MossTestSuite:
    """
    return a MossTestSuite
    """
    container = moss_container()
    return MossTestSuite(container)
