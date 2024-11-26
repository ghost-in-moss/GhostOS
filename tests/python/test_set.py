def test_set_len():
    s = {1, 2, 3}
    assert len(s) == 3


def test_set_order():
    for i in range(10):
        a = [1, 2, 3]
        b = set(a)
        c = []
        for k in b:
            c.append(k)
        assert a == c
