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
