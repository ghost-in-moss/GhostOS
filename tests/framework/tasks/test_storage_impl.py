from ghostos.framework.storage import MemStorage
from ghostos.framework.tasks.storage_tasks import StorageGoTasksImpl
from ghostos.framework.logger import FakeLogger
from ghostos.core.runtime import GoTaskStruct, TaskBrief
from ghostos.entity import EntityMeta


def test_storage_tasks_impl():
    storage = MemStorage()
    tasks = StorageGoTasksImpl(storage, FakeLogger())
    task = GoTaskStruct.new(
        task_id="task_id",
        process_id="process_id",
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

    assert TaskBrief.from_task(task) == TaskBrief.from_task(new_got)
