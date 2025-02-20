from ghostos_container import Container
from ghostos_moss.abcd import (
    Moss, MossCompiler, MossRuntime, MossPrompter, Execution,
    AttrPrompts, Injection,
    MOSS_VALUE_NAME, MOSS_TYPE_NAME, MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
)
from ghostos_moss.moss_impl import DefaultMOSSProvider
from ghostos_moss.testsuite import MossTestSuite
from ghostos_moss.pycontext import PyContext
from ghostos_moss.exports import Exporter
from ghostos_moss.magics import __is_subclass__, __is_instance__, MagicPrompter
from ghostos_moss.prompts import PromptAbleClass, PromptAbleObj

__all__ = [
    # abstract contracts
    Moss, MossCompiler, MossRuntime, MossPrompter, Execution,
    # constants
    MOSS_VALUE_NAME, MOSS_TYPE_NAME, MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
    # types
    AttrPrompts,
    # pycontext related
    PyContext,
    # testing
    DefaultMOSSProvider,
    MossTestSuite,

    Exporter,  # useful to exports values in group, and other module will reflect them in moss_imported_attrs_prompt
    'moss_container',
    'moss_test_suite',

    # magic prompters
    __is_subclass__,
    __is_instance__,
    MagicPrompter,

    PromptAbleClass, PromptAbleObj,
]


def moss_container() -> Container:
    """
    test container for Moss
    """
    from ghostos.contracts.modules import DefaultModulesProvider
    container = Container()
    container.register(DefaultMOSSProvider())
    container.register(DefaultModulesProvider())
    return container


def moss_test_suite() -> MossTestSuite:
    """
    return a MossTestSuite
    """
    container = moss_container()
    return MossTestSuite(container)
