import time

from ghostos_moss import moss_container
from ghostos_moss.abcd import MossCompiler, Moss, MOSS_TYPE_NAME, MossRuntime
from ghostos_moss.pycontext import PyContext
from ghostos_moss.examples import baseline
from ghostos_moss.modules import ImportWrapper
from ghostos_container import Container


def test_baseline_exec():
    container = moss_container()
    compiler = container.force_fetch(MossCompiler)
    compiler = compiler.injects(bar=123)
    assert compiler is not None

    # join context
    compiler.join_context(PyContext(module=baseline.__name__))
    assert compiler.pycontext().module == baseline.__name__
    # 获取目标代码.
    # code = compiler.pycontext_code()

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
    # assert isinstance(moss, moss_type)

    prompter = runtime.prompter()
    assert prompter is not None
    prompt = prompter.dump_module_prompt()

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

    # 动态加载的 attr.
    assert "life" in result.pycontext.properties, f"life is not found in dumped pycontext {result.pycontext}"
    life = result.pycontext.properties["life"]
    assert life is not None
    # 生命周期被执行.
    value = result.pycontext.get_prop("life")
    assert isinstance(value, list)
    assert "__moss_compile__" in value, "in array test"
    assert '__moss_compile__' in value, "__moss_compile__ not found"
    assert 123 == result.pycontext.get_prop("bar")

    moss = runtime.moss()
    # 验证用 injections 注入.
    assert getattr(moss, 'bar') == 123
    # 验证依赖注入.
    foo = getattr(moss, 'foo')
    Foo = runtime.module().__dict__['Foo']
    assert Foo is baseline.Foo
    moss.fetch(Foo)
    assert foo is not None and isinstance(foo, Foo)
    assert foo.foo() == "hello"

    # 最后成功销毁.
    runtime.close()
    container.shutdown()


def test_baseline_in_test_mode():
    container = moss_container()
    compiler = container.force_fetch(MossCompiler)
    assert compiler is not None

    # join context
    compiler.join_context(PyContext(module=baseline.__name__))
    assert compiler.pycontext().module == baseline.__name__

    # 获取目标代码.
    with compiler:
        runtime = compiler.compile("__test__")
        assert runtime is not None

        module = runtime.module()
        # 名字相同.
        assert module.__name__ != baseline.__name__
        assert module.__name__ == "__test__"
        with runtime:
            moss = runtime.moss()
            moss.hello = "world"
            result = runtime.execute(target="test_main", local_args=["moss"])
            assert result.returns == 3
            assert result.pycontext.get_prop("hello") == "world"
    container.shutdown()


def test_baseline_with_pycontext_code():
    container = moss_container()
    compiler = container.force_fetch(MossCompiler)
    assert compiler is not None
    # join context
    line = "print('hello')"
    compiler.join_context(PyContext(module=baseline.__name__, code=line))
    assert line in compiler.pycontext_code()
    container.shutdown()


def test_moss_gc():
    from threading import Thread
    from gc import collect
    from ghostos_moss.moss_impl import MossStub, MossTempModuleType
    container = moss_container()
    container_count = Container.instance_count
    moss_stub_count = MossStub.instance_count

    def run(c: Container):
        compiler = c.force_fetch(MossCompiler)
        compiler = compiler.join_context(PyContext(module=baseline.__name__))
        runtime = compiler.compile("__test__")
        assert runtime.moss() is not None
        assert MossRuntime.instance_count > 0
        assert MossStub.instance_count > 0
        assert MossTempModuleType.__instance_count__ > 0
        with runtime:
            runtime.execute(target="test_main", local_args=["moss"])

    threads = []
    for i in range(10):
        t = Thread(target=run, args=(container,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    # assert gc success
    collect()
    time.sleep(0.05)
    assert MossTempModuleType.__instance_count__ < 10
    assert MossRuntime.instance_count == 0
    assert MossStub.instance_count <= moss_stub_count
    assert Container.instance_count < (10 + container_count)
