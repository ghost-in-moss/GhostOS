from ghostiss.core.moss2.abc import MOSSCompiler, MOSS
from ghostiss.core.moss2.impl import TestMOSSProvider
from ghostiss.core.moss2.pycontext import PyContext
from ghostiss.core.moss2.libraries import DefaultModulesProvider, ImportWrapper
from ghostiss.core.moss.reflect import (
    Importing, Attr,
)
from ghostiss.container import Container
from ghostiss.core.moss2.examples import baseline
from pydantic import BaseModel


def prepare_container() -> Container:
    container = Container()
    container.register(TestMOSSProvider())
    container.register(DefaultModulesProvider())
    return container


def test_baseline_exec():
    container = prepare_container()
    compiler = container.force_fetch(MOSSCompiler)
    assert compiler is not None

    # join context
    compiler.join_context(PyContext(module=baseline.__name__))
    assert compiler.pycontext().module == baseline.__name__
    # 获取目标代码.
    code = compiler.pycontext_code()
    assert "baseline" in code
    assert "from __future__" in code

    modulename = "__test__"
    runtime = compiler.compile(modulename)
    assert runtime is not None
    module = runtime.module()
    # 名字相同.
    assert module.__name__ == modulename

    # 先测试 ctx
    with runtime.runtime_ctx():
        print("hello")
    buffed = runtime.dump_std_output()
    assert buffed.startswith("hello")

    moss_type = runtime.moss_type()
    # 使用了默认的 MOSS
    assert moss_type is MOSS
    moss = runtime.moss()
    assert isinstance(moss, MOSS)

    prompter = runtime.prompter()
    assert prompter is not None
    prompt = prompter.dump_context_prompt()

    assert 'def plus' in prompt
    # 在 moss 标记内的不展示.
    assert "__test__" not in prompt

    result = runtime.execute(target="main", args=["moss"])
    assert result.returns == 3
    assert result.std_output.startswith("hello")

    # 最后成功销毁.
    runtime.destroy()


def test_baseline_with_pycontext_code():
    container = prepare_container()
    compiler = container.force_fetch(MOSSCompiler)
    assert compiler is not None

    # join context
    line = "print('hello')"
    compiler.join_context(PyContext(module=baseline.__name__, code=line))
    assert line in compiler.pycontext_code()
