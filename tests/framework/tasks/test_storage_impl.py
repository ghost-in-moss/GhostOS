from ghostos.framework.storage import MemStorage
from ghostos.framework.tasks.storage_tasks import StorageGoTasksImpl
from ghostos.framework.logger import FakeLogger
from ghostos.core.runtime import GoTaskStruct, TaskBrief
from ghostos_common.entity import EntityMeta
import time


def test_storage_tasks_impl():
    storage = MemStorage()
    tasks = StorageGoTasksImpl(storage, FakeLogger())
    task = GoTaskStruct.new(
        task_id="task_id",
        shell_id="shell_id",
        process_id="process_id",
        depth=0,
        name="name",
        description="description",
        meta=EntityMeta(type="type", content=""),
    )

    t = tasks.get_task(task.task_id)
    assert t is None
    tasks.save_task(task)
    t = tasks.get_task(task.task_id)
    assert t is not None

    with tasks.lock_task(task.task_id):
        locker = tasks.lock_task(task.task_id)
        new_turn = task.new_turn()
        tasks.save_task(new_turn)
        assert locker.acquire() is False

    locker = tasks.lock_task(task.task_id)
    assert locker.acquire() is True
    locker.release()

    new_got = tasks.get_task(task.task_id)
    assert new_got != task
    assert new_got == new_turn

    t1 = TaskBrief.from_task(task)
    t2 = TaskBrief.from_task(new_got)
    t1.created = t2.created
    t1.updated = t2.updated
    assert t1 == t2


def test_storage_tasks_impl_lock():
    storage = MemStorage()
    tasks = StorageGoTasksImpl(storage, FakeLogger())
    locker = tasks.lock_task("task_id", overdue=0.1)
    assert not locker.acquired()
    for i in range(5):
        time.sleep(0.05)
        assert locker.acquire()
        assert locker.acquired()
    assert locker.release()
    assert not locker.acquired()
    with locker:
        assert locker.acquired()
    assert not locker.acquired()
