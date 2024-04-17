import inspect


def test_get_source():
    """
    test inspect getsource with doc and codes
    """
    # data is str; comment is part of the codes.
    data = inspect.getsource(test_get_source)
    assert "inspect.getsource" in data and "assert" in data
    assert "test" in data
    assert "# data is str" in data


def test_get_source_from_obj():
    fn = test_get_source
    data = inspect.getsource(fn)
    assert "test" in data


def test_class_object_source():
    class Test:
        foo: str

    t = Test()
    # can not get source from instance
    data = inspect.getsource(t)
    e = None
    try:
        assert "class Test" in data
    except TypeError as exp:
        e = exp
    finally:
        assert e is not None
