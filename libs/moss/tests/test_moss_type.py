from abc import ABCMeta
from ghostos_moss import get_moss_compiler, MOSS_TYPE_NAME, Moss as Parent
import inspect


def test_module_without_moss_type_has_one():
    assert issubclass(type(Parent), ABCMeta)
    assert inspect.isabstract(Parent)
    compiler = get_moss_compiler()
    with compiler:
        rtm = compiler.compile(__name__)
        assert MOSS_TYPE_NAME in rtm.prompter().get_imported_attrs()

        prompt = rtm.prompter().dump_imported_prompt()
        assert "Moss(" in prompt


def test_with_default_moss_type():
    from ghostos_moss.examples.random_moss import RandomMoss
    compiler = get_moss_compiler()
    compiler.with_default_moss_type(RandomMoss)
    with compiler:
        rtm = compiler.compile(__name__)
        assert rtm.module().__dict__["Moss"] is RandomMoss
        assert rtm.moss_type() is RandomMoss
        prompt = rtm.prompter().dump_imported_prompt()
        assert "RandomMoss(" in prompt

        prompt = rtm.prompter().get_imported_attrs_prompt()
        assert "RandomMoss(" in prompt
