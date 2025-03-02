def foo() -> str:
    return 'foo'


def test_exec_with_method():
    local_values = {'foo': foo, 'result': None}
    code = """
result = foo()
"""
    exec(code, globals(), local_values)
    assert local_values['result'] == "foo"
