from ghostos_common.helpers.code_analyser import (
    get_code_interface, get_attr_source_from_code, get_attr_interface_from_code,
    get_code_interface_str,
)


def test_get_code_interface_baseline():
    code = """
import os
from typing import List, TypeVar

T = TypeVar('T')

__all__ = ['MyClass']

'''hello world'''

class MyClass(Generic[T], ABC):
    \"\"\"This is class doc.\"\"\"
    
    a: List[T] = []
    
    class Subclass(BaseModel):
    
        attr: int = Field(
            default=123, 
            description="hello"
                        "world"
        )
    
    
    def __init__(self):
        super().__init__()
        self._private_var = 42
        self.public_var = 100

    def public_method(self):
        \"\"\"This is a public method.\"\"\"
        a = b + 1
        return a
        
    @staticmethod
    def static():
        return 123
        
    @classmethod
    def classmethod(cls):
        return 123
        
    @abstractmethod
    def abstract(cls):
        '''
        abstract
        '''
        return 123
    

    def _private_method(self):
        pass

def my_function(
    a: int,
    b
):
    \"\"\"This is a function.\"\"\"
    a = b + 1
    return a

@decorator
def decorated_function(a: int, b: int) -> int:
    \"\"\"This is a function.\"\"\"
    a = b + 1
    return a
"""

    interface = "\n\n".join(get_code_interface(code))
    assert "__all__" in interface
    assert "T = TypeVar('T')" in interface
    assert "'''hello world'''" in interface

    assert """
    @abstractmethod
    def abstract(cls):
        '''
        abstract
        '''
        pass
""" in interface

    assert """
    @classmethod
    def classmethod(cls):
        pass
"""
    assert """
class MyClass(Generic[T], ABC):
    \"\"\"This is class doc.\"\"\"
""" in interface

    attr_sources = get_attr_source_from_code(code)
    assert 'MyClass' in attr_sources
    assert 'my_function' in attr_sources
    assert 'decorated_function' in attr_sources

    attr_interfaces = get_attr_interface_from_code(code)
    assert 'MyClass' in attr_interfaces
    assert 'my_function' in attr_interfaces
    assert 'decorated_function' in attr_interfaces

    for name in attr_sources:
        source = attr_sources[name]
        interface = get_code_interface_str(source)
        attr_interface = attr_interfaces[name]
        assert interface == attr_interface
