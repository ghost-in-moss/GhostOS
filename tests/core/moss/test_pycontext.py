from ghostiss.core.moss import PyContext, Imported, Variable


def test_pycontext_imported():
    c = PyContext()
    c.add_import(Imported(module="foo", spec="bar"))
    assert len(c.imported) == 1


def test_pycontext_join_baseline():
    left = PyContext()
    right = PyContext()
    right.add_import(Imported(module="foo", spec="bar"))
    joined = left.join(right)
    assert len(left.imported) == 0
    assert len(right.imported) == 1
    assert len(joined.imported) == 1
