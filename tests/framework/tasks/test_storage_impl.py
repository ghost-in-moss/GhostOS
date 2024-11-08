from ghostos.framework.storage import MemStorage
from ghostos.framework.tasks.storage_tasks import StorageGoTasksImpl
from ghostos.framework.logger import FakeLogger
from ghostos.core.runtime import GoTaskStruct
from ghostos.entity import EntityMeta


def test_storage_tasks_impl():
    storage = MemStorage()
    tasks = StorageGoTasksImpl(storage, FakeLogger())
    task = GoTaskStruct.new(
        task_id="task_id",
        shell_id="session_id",
        process_id="process_id",
        name="name",
        description="description",
        meta=EntityMeta(type="type", data={}),
    )

    t = tasks.get_task(task.task_id, False)
    assert t is None
    tasks.save_task(task)
    t = tasks.get_task(task.task_id, False)
    assert t is not None
    assert t.lock is None

    locked = tasks.get_task(task.task_id, True)
    assert locked.lock is not None
    locked2 = tasks.get_task(task.task_id, True)
    assert locked2 is None
    tasks.unlock_task(locked.task_id, locked.lock)

    locked2 = tasks.get_task(task.task_id, True)
    assert locked2.lock is not None

    new_lock = tasks.refresh_task_lock(locked2.task_id, locked2.lock)
    assert new_lock is not locked2.lock
