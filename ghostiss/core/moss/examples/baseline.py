from abc import ABC, abstractmethod
from typing import Optional, List
from ghostiss.core.moss.abc import Moss as Parent, attr
from inspect import getsource, getmembers


class Foo(ABC):
    """定义一个本地类, 用来做依赖注入测试. """

    @abstractmethod
    def foo(self) -> str:
        pass


def plus(a: int, b: int) -> int:
    """ 验证本地方法存在于 prompt. """
    return a + b


class Moss(Parent):
    """
    本地定义的 Moss 类. 每个 MOSS 文件里都应该有一个 Moss 类, 可以是 import 的也可以是本地定义的.
    记得它要继承自 Moss.
    """
    life: List[str] = attr(default_factory=list, desc="用来记录发生过的生命周期.")
    """测试 attr 方法用来定义可持久化的属性. """

    foo: Foo
    """依赖注入 Foo 的测试用例. """


# <moss>
# !!! 使用 `# <moss>` 和 `# </moss>` 包裹的代码不会对大模型呈现.

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ghostiss.core.moss.abc import MossCompiler, MossRuntime, AttrPrompts, MossPrompter, MossResult


def __moss_compile__(compiler: "MossCompiler") -> "MossCompiler":
    """
    从 compile 中获取 MOSSRuntime, 并对它进行初始化.
    可选的魔术方法. 如果定义的话, MOSS 执行 compile 的阶段会默认执行它.

    主要解决各种注入方面的需求:
    """
    # 单测里应该有这个. moss.bar == 123
    compiler.injects(bar=123)
    # 插入生命周期事件, 直接赋值到 moss 上.
    Moss.life.append("__moss_compile__")

    # 准备依赖注入 Foo.
    class FooImpl(Foo):
        def foo(self) -> str:
            return "hello"

    from ghostiss.container import provide
    # 用这种方式, 可以预期 Moss 被依赖注入了 Foo, 注入的是 FooImpl
    provider = provide(Foo, singleton=False)(lambda con: FooImpl())
    compiler.register(provider)

    return compiler


def __moss_attr_prompts__() -> "AttrPrompts":
    Moss.life.append("__moss_attr_prompts__")
    return [
        # 重写了 getsource 的 prompt, 它就应该不存在了.
        ("getsource", ""),
        # 添加一个意义不明的注释. 也应该在 prompt 里.
        ("9527", "# hello world")
    ]


def __moss_prompt__(prompter: "MossPrompter") -> str:
    # 测试生命周期生效.
    Moss.life.append("__moss_prompt__")
    from ghostiss.core.moss.lifecycle import __moss_prompt__
    return __moss_prompt__(prompter)


def __moss_exec__(*args, **kwargs) -> "MossResult":
    # 测试生命周期生效.
    Moss.life.append("__moss_exec__")
    from ghostiss.core.moss.lifecycle import __moss_exec__
    return __moss_exec__(*args, **kwargs)


if __name__ == '__test__':
    """
    用这种方式定义的代码可以直接用来做单元测试. 
    """


    def main(moss: Moss) -> int:
        """
        模拟一个 main 方法, 测试 moss 的调用.
        assert 返回值是 3. 外部的 MOSSRuntime 调用这个方法.
        详见 __test__
        """
        return plus(1, 2)


    def __test__(runtime: "MossRuntime") -> str:
        """
        直接把测试用例集成到系统里都可以.
        就是这么霸气.
        """
        try:

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
            assert getattr(moss, "foo") is 123

            # 运行 main 方法.
            result = runtime.execute(target="main", args=["moss"])
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
            assert "__moss_compile__" in life
            assert "__moss_attr_prompts__" in life
            assert "__moss_prompt__" in life
            assert "__moss_exec__" in life

            moss = runtime.moss()
            # 验证用 injections 注入.
            assert getattr(moss, 'bar') == 123
            # 验证依赖注入.
            foo = getattr(moss, 'foo')
            assert foo is not None and isinstance(foo, Foo)
            assert foo.foo() == "hello"
        except AssertionError as e:
            return str(e)
        return ""

# </moss>
