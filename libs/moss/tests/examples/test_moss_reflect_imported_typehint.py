from ghostos_moss import moss_runtime_ctx
from ghostos_moss.examples.funcs_with_typing import *


def test_moss_reflect_imported_typehint():
    with moss_runtime_ctx(__name__) as rtm:
        imported_attrs = rtm.prompter().get_imported_attrs()
        assert "A" in imported_attrs
        assert "dict[int, str]" in str(rtm.prompter().get_imported_attrs_prompt())
