def test_with_statement():
    class Foo:
        error = None

        def __enter__(self):
            return self

        def run(self):
            raise RuntimeError("failed")

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_val:
                self.error = exc_val
                return True

    with Foo() as foo:
        foo.run()

    assert foo.error is not None
    assert isinstance(foo.error, RuntimeError)
