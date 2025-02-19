import time


class FooCommand:

    def __init__(self, content: str, duration: float):
        self.content = content
        self.duration = duration

    def run(self):
        start = time.time()
        now = time.time()
        while now - start < self.duration:
            print(self.content)
            time.sleep(1)
            now = time.time()


def test_stop_able_threads():
    from multiprocessing import Process

    t = FooCommand('hello', 2)
    p = Process(target=t.run, args=())
    p.start()
    p.terminate()
    p.join()
