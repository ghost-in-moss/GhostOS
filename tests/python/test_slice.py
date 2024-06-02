def test_slice_pop_and_insert():
    k = [0, 1, 2]
    v = k.copy()
    assert 0 == v.pop(0)
    assert len(v) == 2
    v.insert(0, 0)
    assert k == v

