from ghostos.core.moss import test_container
from ghostos.core.moss.abc import MossCompiler, Moss, MOSS_TYPE_NAME
from ghostos.core.moss.pycontext import PyContext
from ghostos.core.moss.examples import baseline
from ghostos.contracts.modules import ImportWrapper


def test_baseline_exec():
    container = test_container()
    compiler = container.force_fetch(MossCompiler)
    assert compiler is not None

    # join context
    compiler.join_context(PyContext(module=baseline.__name__))
    assert compiler.pycontext().module == baseline.__name__
    # 获取目标代码.
    code = compiler.pycontext_code()
    assert "from __future__" in code

    runtime = compiler.compile(None)
    assert runtime is not None

    module = runtime.module()
    # 名字相同.
    assert module.__name__ == baseline.__name__
    #
    importer = module.__dict__.get('__import__', None)
    assert isinstance(importer, ImportWrapper)

    # 先测试 ctx
    # with runtime.runtime_ctx():
    #     print("hello")
    # buffed = runtime.dump_std_output()
    # assert buffed.startswith("hello")

    exists_moss_type = module.__dict__.get(MOSS_TYPE_NAME)
    moss_type = runtime.moss_type()
    # 使用了默认的 MOSS
    assert issubclass(moss_type, Moss)
    assert moss_type is exists_moss_type

    moss = runtime.moss()
    assert isinstance(moss, Moss)
    assert isinstance(moss, moss_type)

    prompter = runtime.prompter()
    assert prompter is not None
    prompt = prompter.dump_context_prompt()

    # plus 方法存在.
    assert 'def plus' in prompt
    # 在 moss 标记内的不展示.
    assert "__test__" not in prompt
    # 虽然import 了 inspect 的两个方法, 但一个的 prompt 被重置了.
    assert "def getmembers(" in prompt
    assert "def getsource(" not in prompt
    # 添加的意义不明的注释也应该存在了.
    assert "# hello world" in prompt

    # assert moss
    moss = runtime.moss()
    assert getattr(moss, "bar") is 123

    # 运行 main 方法.
    result = runtime.execute(target="test_main", local_args=["moss"])
    # main 方法的运行结果.
    assert result.returns == 3
    # 测试 print 仍然有效.
    assert result.std_output.startswith("hello")

    # 动态加载的 attr.
    assert "life" in result.pycontext.properties, f"life is not found in dumped pycontext {result.pycontext}"
    life = result.pycontext.properties["life"]
    assert life is not None
    # 生命周期被执行.
    value = life.value
    assert isinstance(value, list)
    assert "__moss_compile__" in ["__moss_compile__"], "in array test"
    assert '__moss_compile__' in value, "__moss_compile__ not found"
    assert "__moss_attr_prompts__" in value, "__moss_attr_prompts__ not found"
    assert "__moss_prompt__" in value, "__moss_prompt__ not found"
    assert "__moss_exec__" in value, "__moss_exec__ not found"

    moss = runtime.moss()
    # 验证用 injections 注入.
    assert getattr(moss, 'bar') == 123
    # 验证依赖注入.
    foo = getattr(moss, 'foo')
    Foo = runtime.module().__dict__['Foo']
    assert foo is not None and isinstance(foo, Foo)
    assert foo.foo() == "hello"

    # 最后成功销毁.
    runtime.destroy()


def test_baseline_in_test_mode():
    container = test_container()
    compiler = container.force_fetch(MossCompiler)
    assert compiler is not None

    # join context
    compiler.join_context(PyContext(module=baseline.__name__))
    assert compiler.pycontext().module == baseline.__name__

    # 获取目标代码.
    runtime = compiler.compile("__test__")
    assert runtime is not None

    module = runtime.module()
    # 名字相同.
    assert module.__name__ != baseline.__name__
    assert module.__name__ == "__test__"
    hack_import = module.__dict__.get('__import__', None)
    # 这时就不是原来的 module 了.
    assert hack_import is not None
    assert isinstance(hack_import, ImportWrapper)

    # 先测试 ctx
    # with runtime.runtime_ctx():
    #     print("hello")
    # buffed = runtime.dump_std_output()
    # assert buffed.startswith("hello")

    exists_moss_type = module.__dict__.get(MOSS_TYPE_NAME)
    moss_type = runtime.moss_type()
    # 使用了默认的 MOSS
    assert issubclass(moss_type, Moss)
    assert moss_type is exists_moss_type

    moss = runtime.moss()
    assert isinstance(moss, Moss)
    assert isinstance(moss, moss_type)

    prompter = runtime.prompter()
    assert prompter is not None
    prompt = prompter.dump_context_prompt()

    # 独立编译的模块和之前一样.
    # plus 方法存在.
    assert 'def plus' in prompt
    # 在 moss 标记内的不展示.
    assert "__test__" not in prompt
    # 虽然import 了 inspect 的两个方法, 但一个的 prompt 被重置了.
    assert "def getmembers(" in prompt
    assert "def getsource(" not in prompt
    # 添加的意义不明的注释也应该存在了.
    assert "# hello world" in prompt

    # assert moss
    moss = runtime.moss()
    assert getattr(moss, "bar") is 123

    # 运行 main 方法.
    result = runtime.execute(target="main", local_args=["moss"])
    # main 方法的运行结果.
    assert result.returns == 4

    # 动态加载的 attr.
    assert "life" in result.pycontext.properties, f"life is not found in dumped pycontext {result.pycontext}"
    life = result.pycontext.properties["life"]
    assert life is not None
    # 生命周期被执行.
    value = life.value
    assert isinstance(value, list)
    assert "__moss_compile__" in value, "__moss_compile__ not found"

    moss = runtime.moss()
    # 验证用 injections 注入.
    assert getattr(moss, 'bar') == 123
    # 验证依赖注入.
    foo = getattr(moss, 'foo')
    Foo = runtime.module().__dict__['Foo']
    assert foo is not None and isinstance(foo, Foo)
    assert foo.foo() == "hello"

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
