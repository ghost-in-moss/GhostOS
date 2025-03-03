from ghostos_common.helpers import get_code_interface_str, code_syntax_check
import inspect


def test_get_code_interface_str():
    async def foo() -> int:
        return 42

    code = inspect.getsource(foo)
    interface = get_code_interface_str(code)
    assert "async def foo()" in interface
    assert code_syntax_check(code) is None
