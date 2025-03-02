from ghostos_common.helpers import get_code_interface_str
import inspect


def test_get_code_interface_str():
    async def foo() -> int:
        return 42

    code = inspect.getsource(foo)
    interface = get_code_interface_str(code)
    assert "async def foo()" in interface
