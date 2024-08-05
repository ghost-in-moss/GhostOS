def test_exec_read_source():
    from types import ModuleType
    code = """
def foo() -> str:
    return 'foo'
"""
    test = ModuleType('test_exec')
    exec(code, test.__dict__)

    from tree_sitter_languages import get_parser
    parser = get_parser('python')
    tree = parser.parse(code.encode('utf-8'))

    foo = tree.root_node.children[0]
    assert foo is not None
    assert foo.text == code.strip().encode('utf-8')


def test_tree_sitter_baseline():
    code = """
from abc import ABC, abstractmethod
from typing import (
    Optional, Tuple, List as L,
)
class Bar(ABC):
    @property
    @abstractmethod
    def bar(self) -> str:
        return 'bar'
        
class Foo:
    '''test'''
    foo: int = 1
    bar: Bar

f = Foo() 
a: Optional[int] = 123
"""
    from tree_sitter_languages import get_parser
    parser = get_parser('python')
    tree = parser.parse(code.encode('utf-8'))
    assert tree is not None
