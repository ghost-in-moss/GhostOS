from ghostos.container import Container
from ghostos.core.moss.abc import (
    Moss, MossCompiler, MossRuntime, MossPrompter, Execution,
    AttrPrompts,
    MOSS_VALUE_NAME, MOSS_TYPE_NAME, MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
    MOSS_EXEC_EVENT, MOSS_PROMPT_EVENT, MOSS_COMPILE_EVENT, MOSS_ATTR_PROMPTS_EVENT,
    moss_message,
)
from ghostos.core.moss.impl import DefaultMOSSProvider
from ghostos.core.moss.test_suites import MossTestSuite
from ghostos.core.moss.pycontext import PyContext, Injection, Property, attr, SerializableType, SerializableData
from ghostos.core.moss.functional_token import (
    DEFAULT_MOSS_FUNCTIONAL_TOKEN,
    DEFAULT_MOSS_PROMPT_TEMPLATE,
    get_default_moss_prompt,
)

__all__ = [
    # abstract contracts
    Moss, MossCompiler, MossRuntime, MossPrompter, Execution,
    # constants
    MOSS_VALUE_NAME, MOSS_TYPE_NAME, MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
    MOSS_EXEC_EVENT, MOSS_PROMPT_EVENT, MOSS_COMPILE_EVENT, MOSS_ATTR_PROMPTS_EVENT,
    DEFAULT_MOSS_FUNCTIONAL_TOKEN,
    DEFAULT_MOSS_PROMPT_TEMPLATE,
    # methods
    get_default_moss_prompt,
    # types
    AttrPrompts,
    # pycontext related
    PyContext, Injection, Property, attr, SerializableType, SerializableData,
    # testing
    DefaultMOSSProvider,
    MossTestSuite,
    'test_container',
    'moss_test_suite',

]


def test_container() -> Container:
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
    container = test_container()
    return MossTestSuite(container)
