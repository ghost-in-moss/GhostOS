from ghostos.container import Container
from ghostos.core.moss.abc import (
    Moss, MossCompiler, MossRuntime, MossPrompter, MossResult,
    AttrPrompts,
    MOSS_NAME, MOSS_TYPE_NAME, MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
    MOSS_EXEC_EVENT, MOSS_PROMPT_EVENT, MOSS_COMPILE_EVENT, MOSS_ATTR_PROMPTS_EVENT
)
from ghostos.core.moss.impl import TestMOSSProvider
from ghostos.core.moss.test_suites import MossTestSuite
from ghostos.core.moss.pycontext import PyContext, Injection, Property, attr, SerializableType, SerializableData
from ghostos.core.moss.functional_token import (
    DEFAULT_MOSS_FUNCTIONAL_TOKEN,
    DEFAULT_MOSS_PROMPT_TEMPLATE,
    get_default_moss_prompt,
)


def test_container() -> Container:
    from ghostos.contracts.modules import DefaultModulesProvider
    container = Container()
    container.register(TestMOSSProvider())
    container.register(DefaultModulesProvider())
    return container
