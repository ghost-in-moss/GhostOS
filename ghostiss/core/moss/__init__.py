from ghostiss.container import Container
from ghostiss.core.moss.abc import (
    Moss, MossCompiler, MossRuntime, MossPrompter, MossResult,
    MOSS_NAME, MOSS_TYPE_NAME, MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
    MOSS_EXEC_EVENT, MOSS_PROMPT_EVENT, MOSS_COMPILE_EVENT, MOSS_ATTR_PROMPTS_EVENT
)
from ghostiss.core.moss.impl import TestMOSSProvider
from ghostiss.core.moss.libraries import (
    DefaultModulesProvider,
    DefaultModules,
    Modules,
)


def test_container() -> Container:
    container = Container()
    container.register(TestMOSSProvider())
    container.register(DefaultModulesProvider())
    return container
