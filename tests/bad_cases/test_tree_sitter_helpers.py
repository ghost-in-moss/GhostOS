from ghostos_common.helpers import code_syntax_check
import inspect


def foo():
    return 123


def test_code_syntax_check():
    source = inspect.getsource(foo)
    assert code_syntax_check(source) is None
