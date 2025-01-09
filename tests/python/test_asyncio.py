import asyncio
import concurrent


def test_loop_run_until_complete():
    async def foo():
        return 123

    loop = asyncio.new_event_loop()
    loop.run_until_complete(foo())


def test_gather():
    async def bar():
        await asyncio.sleep(0.1)
        # print("bar")
        return 123

    async def baz():
        # print("baz")
        return 123

    async def foo():
        await asyncio.gather(bar(), baz())

    lp = asyncio.new_event_loop()
    lp.run_until_complete(foo())

# for 3.12
# def test_producer_and_consumer():
#     class Main:
#         stop = False
#
#         got = []
#
#         async def _producer(self, q: asyncio.Queue):
#             count = 0
#             while not self.stop:
#                 q.put_nowait(count)
#                 count += 1
#                 await asyncio.sleep(0.1)
#
#         async def _consumer(self, q: asyncio.Queue):
#             while not self.stop:
#                 v = await q.get()
#                 self.got.append(v)
#                 self.stop = v > 2
#
#         async def run(self):
#             async with asyncio.TaskGroup() as tg:
#                 q = asyncio.Queue()
#                 tg.create_task(self._producer(q))
#                 tg.create_task(self._consumer(q))
#
#     main = Main()
#     asyncio.run(main.run())
#     assert main.got == [0, 1, 2, 3]
