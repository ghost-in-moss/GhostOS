from ghostos.contracts.pool import DefaultPool


def test_default_pool():
    class Foo:
        count = 0

        def go(self):
            self.count += 1

    pool = DefaultPool(4)
    foo = Foo()
    pool.submit(foo.go)
    pool.submit(foo.go)
    pool.submit(foo.go)
    pool.submit(foo.go)
    pool.shutdown()
    assert foo.count == 4
