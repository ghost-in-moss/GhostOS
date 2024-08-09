import inspect
from ghostiss.core.moss import prompts
from ghostiss.core.moss.prompts import reflect_module_locals, compile_attr_prompts

import unittest

from ghostiss.core.moss.impl import MossRuntimeImpl
from ghostiss.core.moss.abc import (
    MOSS_HIDDEN_MARK, MOSS_HIDDEN_UNMARK,
)


def test_prompts_baseline():
    assert inspect.ismodule(prompts)
    # inspect 也被 prompts 库引用了.
    assert not inspect.isbuiltin(inspect)
    attr_prompts = reflect_module_locals("ghostiss.core.moss.prompts", prompts.__dict__)
    data = {}
    array = []
    for name, prompt in attr_prompts:
        array.append((name, prompt))
        data[name] = prompt
    # 从 utils 模块里定义的.
    assert "is_typing" in data
    # typing 库本身的不会出现.
    assert "Optional" not in data
    # 引用的抽象类应该存在.
    assert "PromptAble" in data

    prompt = compile_attr_prompts(array)
    assert "class PromptAble" in prompt



def test_prompts_mark_judgement():
    parser = MossRuntimeImpl._parse_pycontext_code

    # test_no_hidden_markers
    code1 = """def foo():
        return 42
    print(foo())"""

    expected1 = code1
    assert parser(code1) == expected1

    # test_hidden_markers_with_model_visible
    code2 = f"""def foo():
        return 42
    {MOSS_HIDDEN_MARK}
    def hidden_function():
        return "hidden"
    {MOSS_HIDDEN_UNMARK}
    print(foo())"""

    expected2 = """def foo():
        return 42
    print(foo())"""
    assert parser(code2) == expected2

    # test_hidden_markers_with_model_invisible
    code3 = f"""def foo():
        return 42
    {MOSS_HIDDEN_MARK}
    def hidden_function():
        return "hidden"
    {MOSS_HIDDEN_UNMARK}
    print(foo())"""

    expected3 = f"""def foo():
        return 42
    {MOSS_HIDDEN_MARK}
    def hidden_function():
        return "hidden"
    {MOSS_HIDDEN_UNMARK}
    print(foo())"""
    assert parser(code3, exclude_moss_mark_code=False) == expected3

    # test_multiple_hidden_sections
    code4 = f"""def foo():
        return 42
    {MOSS_HIDDEN_MARK}
    def hidden_function_1():
        return "hidden1"
    {MOSS_HIDDEN_UNMARK}
    def bar():
        return 24
    {MOSS_HIDDEN_MARK}
    def hidden_function_2():
        return "hidden2"
    {MOSS_HIDDEN_UNMARK}
    print(foo())"""

    expected4 = """def foo():
        return 42
    def bar():
        return 24
    print(foo())"""
    assert parser(code4) == expected4

    # test_nested_hidden_markers
    code5 = f"""def foo():
        return 42
    {MOSS_HIDDEN_MARK}
    def hidden_function_1():
        return "hidden1"
        {MOSS_HIDDEN_MARK}
        def hidden_function_2():
            return "hidden2"
        {MOSS_HIDDEN_UNMARK}
        return hidden_function_2()
    {MOSS_HIDDEN_UNMARK}
    print(foo())"""

    expected5 = """def foo():
        return 42
    print(foo())"""
    assert parser(code5) == expected5
