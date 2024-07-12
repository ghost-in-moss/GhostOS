import inspect

from ghostiss.blueprint.moss.moss import MOSS, BasicMOSSImpl, BasicMOSSProvider
from ghostiss.blueprint.moss.modules import BasicModulesProvider
from ghostiss.container import Container
from pydantic import BaseModel


def prepare_container() -> Container:
    container = Container()
    container.register(BasicMOSSProvider())
    container.register(BasicModulesProvider())
    return container


def test_moss_baseline():
    def foo() -> str:
        return "foo"

    class Bar(BaseModel):
        x: int
        y: int

        def bar(self) -> int:
            return self.x + self.y

    c = prepare_container()
    moss = c.force_fetch(MOSS)
    m = moss.new(foo, Bar)
    prompt = m.dump_code_prompt()
    assert "def foo() -> str" in prompt
    assert "class Bar(BaseModel" in prompt

    code = """
result_: str = ""
result_ = os.foo()
"""

    r = m(code=code, target='result_')
    assert r == "foo"
    m.destroy()

    # 尝试运行一个 code 定义的函数.
    m = moss.new(foo, Bar)
    code = """
    
def main(os: MOSS) -> str:
    return os.foo()
"""
    r = m(code=code, target='main', args=['os'])
    assert r == "foo"
