from ghostos_common.helpers.tree_sitter import code_syntax_check


def test_lint_code_success():
    code = """
import inspect

def main():
    print("hello world")
    
source = inspect.getsource(main)
print(source)
"""
    error = code_syntax_check(code.strip())
    assert error is None


def test_lint_code_without_quote():
    code = """
def main():
    print("hello world)

source = inspect.getsource(main)
print(source)
"""
    error = code_syntax_check(code.strip())
    assert error is not None


def test_lint_code_many_errors():
    code = """
def main():
    print("hello world)

source = inspect.getsource(main
print(source)
"""
    error = code_syntax_check(code.strip())
    assert error and "hello world)" in error
