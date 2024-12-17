from queue import Queue


def test_queue():
    q = Queue()
    q.put(None)
    value = q.get(block=True, timeout=5)
    assert value is None
