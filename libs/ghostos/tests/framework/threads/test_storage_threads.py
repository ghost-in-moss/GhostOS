from ghostos.framework.threads import MsgThreadRepoByStorageProvider, GoThreads, GoThreadInfo
from ghostos.framework.storage import MemStorage, Storage
from ghostos.framework.logger import FakeLogger, LoggerItf
from ghostos.core.messages import Message
from ghostos_moss import PyContext
from ghostos_container import Container


def _prepare_container() -> Container:
    container = Container()
    container.set(Storage, MemStorage())
    container.set(LoggerItf, FakeLogger())
    container.register(MsgThreadRepoByStorageProvider())
    return container


def test_threads_baseline():
    thread = GoThreadInfo()
    pycontext = PyContext(module=PyContext.__module__)
    thread.new_turn(None, pycontext=pycontext)
    thread.append(Message.new_tail(content="hello world"))

    tid = thread.id
    container = _prepare_container()
    threads = container.force_fetch(GoThreads)
    threads.save_thread(thread)

    got = threads.get_thread(tid, create=False)
    assert got is not None
    assert got == thread

    fork = threads.fork_thread(got)
    assert fork.id != got.id
    assert fork.root_id == got.id
    assert fork.parent_id == got.id
