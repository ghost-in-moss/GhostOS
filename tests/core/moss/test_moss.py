from ghostiss.core.moss.moss import MOSS, TestMOSSProvider
from ghostiss.core.moss.modules import BasicModulesProvider
from ghostiss.core.moss.reflect import (
    Importing,
)
from ghostiss.container import Container
from pydantic import BaseModel


def prepare_container() -> Container:
    container = Container()
    container.register(TestMOSSProvider())
    container.register(BasicModulesProvider())
    return container


def foo() -> str:
    return "foo"


class Bar(BaseModel):
    x: int
    y: int

    def bar(self) -> int:
        return self.x + self.y


def test_moss_baseline():
    c = prepare_container()
    moss = c.force_fetch(MOSS)

    # test1:
    m = moss.new(foo, Bar)
    prompt = m.dump_code_prompt()
    assert "def foo() -> str" in prompt
    assert "class Bar(BaseModel" in prompt
    assert "class MOSS(ABC):" in prompt

    code = """
result_: str = ""
result_ = os.foo()
"""

    r = m(code=code, target='result_')
    assert r == "foo"
    m.destroy()

    # test2
    # 尝试运行一个 code 定义的函数.
    m = moss.new(foo, Bar)
    code = """
def main(os: MOSS) -> str:
    return os.foo()
"""
    r = m(code=code, target='main', args=['os'])
    assert r == "foo"
    m.destroy()

    m = moss.new(foo, Bar)
    code = """
result_ : int = 0
bar = Bar(x=1, y=2)
result_ = bar.bar()
"""
    assert m(code=code, target='result_') == 3

    # test3
    # 在函数里使用定义过的其它函数.
    m = moss.new(foo, Bar)
    code = """
def plus(v: str) -> str:
    return v + "bar"

def main(os: MOSS) -> str:
    return plus(v=os.foo())
"""
    assert m(code=code, target='main', args=['os']) == "foobar"

    # test4
    # 在函数定义里使用外部提供的变量.
    m = moss.new(foo, Bar)
    code = """
def main(os: MOSS) -> int:
    bar = Bar(x=1, y=2)
    return bar.bar()
"""
    assert m(code=code, target='main', args=['os']) == 3


def test_moss_with_importing():
    c = prepare_container()
    moss = c.force_fetch(MOSS)
    import inspect
    moss.with_vars(Importing(value=inspect))
    prompt = moss.dump_code_prompt()
    assert "import inspect" in prompt


def test_moss_with_func():
    c = prepare_container()
    moss = c.force_fetch(MOSS)
    moss.with_vars(test_moss_with_importing)
    prompt = moss.dump_code_prompt()
    assert "def test_moss_with_importing" in prompt
