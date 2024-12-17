def test_slice_pop_and_insert():
    k = [0, 1, 2]
    v = k.copy()
    assert 0 == v.pop(0)
    assert len(v) == 2
    v.insert(0, 0)
    assert k == v


def test_slice_negative_index():
    arr = [0, 1]
    assert arr[-1] == 1
    assert arr[:-1] == [0]


def test_slice_pop_0():
    arr = [0, 1]
    arr.pop(0)
    arr.pop(0)
    assert arr == []


def test_thread_safe_append():
    from threading import Thread

    threads = []
    target = []
    for i in range(100):
        t = Thread(target=target.append, args=(1,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    # 测试没有线程的报错.
    assert len(target) == 100

    for i in range(100):
        t = Thread(target=target.pop)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
    # 测试没有线程的报错.
    assert len(target) == 0


def test_array_insert_more_than_pointed():
    a = [1, 2, 3, 4]
    a[1:3] = [5, 6, 7, 8]
    assert a == [1, 5, 6, 7, 8, 4]


def test_sort_dicts():
    cases = [
        {'a': 1, 'b': 2, 'c': 3, 'd': 4},
        {'a': 2, 'b': 2, 'c': 3, 'd': 4},
        {'a': 3, 'b': 2, 'c': 3, 'd': 4},
        {'a': 4, 'b': 2, 'c': 3, 'd': 4},
    ]
    values = sorted(cases, key=lambda x: x['a'], reverse=True)
    actual = [c['a'] for c in values]
    assert actual == [4, 3, 2, 1]


def test_arr_tail():
    arr = [1, 2, 3, 4]
    assert arr[-2:] == [3, 4]
    assert arr[-20:] == [1, 2, 3, 4]


def test_negative_slice_index():
    arr = [1, 2, 3, 4]
    first = arr[:2]
    end = arr[2:]
    assert first == [1, 2]
    assert end == [3, 4]
