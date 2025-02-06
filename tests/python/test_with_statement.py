def test_with_error():
    class Foo:
        enter = False
        exited = False

        def __enter__(self):
            self.enter = True

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.exited = True

    foo = Foo()
    e = None
    try:
        with foo:
            raise RuntimeError("hello")
    except RuntimeError as t:
        e = t
    assert e is not None
