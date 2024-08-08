from typing import Callable
from ghostiss.core.moss import test_container
from ghostiss.core.moss.abc import MossCompiler, Moss, MOSS_TYPE_NAME
from ghostiss.core.moss.pycontext import PyContext
from ghostiss.core.moss.examples import baseline
from ghostiss.core.moss.libraries import ImportWrapper


def test_baseline_exec():
    container = test_container()
    compiler = container.force_fetch(MossCompiler)
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
    hack_import = module.__dict__.get('__import__', None)
    assert hack_import is not None
    assert isinstance(hack_import, ImportWrapper)

    # 先测试 ctx
    with runtime.runtime_ctx():
        print("hello")
    buffed = runtime.dump_std_output()
    assert buffed.startswith("hello")

    exists_moss_type = module.__dict__.get(MOSS_TYPE_NAME)
    moss_type = runtime.moss_type()
    # 使用了默认的 MOSS
    assert issubclass(moss_type, Moss)
    assert moss_type is exists_moss_type

    moss = runtime.moss()
    assert isinstance(moss, Moss)
    assert isinstance(moss, moss_type)

    # 直接从编译后的数据里取出 __test__ 方法.
    test = runtime.locals()["__test__"]
    assert isinstance(test, Callable)
    e = test(runtime)
    if e:
        raise AssertionError(e)

    # 最后成功销毁.
    runtime.destroy()


def test_baseline_with_pycontext_code():
    container = test_container()
    compiler = container.force_fetch(MossCompiler)
    assert compiler is not None

    # join context
    line = "print('hello')"
    compiler.join_context(PyContext(module=baseline.__name__, code=line))
    assert line in compiler.pycontext_code()
