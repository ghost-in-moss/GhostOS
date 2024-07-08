from ghostiss.blueprint.moos.exporter import is_builtin
import inspect


def test_is_builtin():
    assert not is_builtin('foo')
    assert not is_builtin(123)
    assert is_builtin(print)
    assert is_builtin(int)
    assert not is_builtin(inspect)
