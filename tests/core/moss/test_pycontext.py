from ghostiss.core.moss.pycontext import PyContext, Injection, Property


def test_pycontext_imported():
    c = PyContext()
    c.inject(Injection(import_from="foo:bar"))
    assert len(c.injections) == 1


def test_pycontext_join_baseline():
    left = PyContext()
    i = Injection.reflect(Injection)
    left.inject(i)
    right = PyContext()
    right.inject(Injection(import_from="foo:bar"))
    joined = left.join(right)
    assert len(left.injections) == 1
    assert len(right.injections) == 1
    assert len(joined.injections) == 2
