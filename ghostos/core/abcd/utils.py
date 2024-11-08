from typing import TypeVar, Optional, Type, Union
from ghostos.helpers import import_class_from_path, generate_import_path, md5
from ghostos.common import get_identifier, to_entity_meta
from ghostos.core.runtime import Runtime, GoTaskStruct
from .concepts import Ghost, GhostDriver

__all__ = [
    'get_ghost_task', 'get_or_create_ghost_task',
    'get_ghost_driver', 'get_ghost_driver_type',
]


def get_ghost_driver_type(ghost: Ghost) -> Type[GhostDriver]:
    """
    get ghost driver instance by default protocol
    """
    if ghost.Driver is not None:
        return ghost.Driver
    name = ghost.__class__.__name__
    module_name = ghost.__class__.__module__
    import_path = f"{module_name}:{name}Driver"
    cls = import_class_from_path(import_path, GhostDriver)
    return cls


def get_ghost_driver(ghost: Ghost) -> GhostDriver:
    ghost_driver_type = get_ghost_driver_type(ghost)
    return ghost_driver_type(ghost)


def is_ghost(value) -> bool:
    try:
        if not isinstance(value, Ghost):
            return False
        id_ = get_identifier(value)
        assert id_ is not None
        meta = to_entity_meta(value)
        assert meta is not None
        driver = get_ghost_driver_type(value)
        assert issubclass(driver, GhostDriver)
        return True
    except AssertionError:
        return False


def make_unique_ghost_id(
        shell_id: str,
        **scope_ids: str,
) -> str:
    """
    make unique ghost id
    :param shell_id: the shell id must exist.
    :param scope_ids:
    :return: md5 hash
    """
    ids = f"shell:{shell_id}"
    keys = sorted(scope_ids.keys())
    for key in keys:
        scope = scope_ids[key]
        ids += f":{key}:{scope}"
    return md5(ids)


def get_or_create_ghost_task(runtime: Runtime, ghost: Ghost, parent_task_id: Optional[str]) -> GoTaskStruct:
    """
    default way to find or create ghost task
    :param runtime:
    :param ghost:
    :param parent_task_id:
    :return:
    """
    task = get_ghost_task(runtime, ghost, parent_task_id)
    if task is None:
        task = make_ghost_task(runtime, ghost, parent_task_id)
    return task


def get_ghost_task(runtime: Runtime, ghost: Ghost, parent_task_id: Optional[str]) -> Union[GoTaskStruct, None]:
    driver = get_ghost_driver(ghost)
    task_id = driver.make_task_id(runtime, parent_task_id)
    task = runtime.tasks.get_task(task_id)
    if task is None:
        return None
    # update task's meta from ghost.
    task.meta = to_entity_meta(ghost)
    return task


def make_ghost_task(runtime: Runtime, ghost: Ghost, parent_task_id: Optional[str]) -> GoTaskStruct:
    """
    default way to create a task
    :param runtime:
    :param ghost:
    :param parent_task_id:
    :return:
    """
    driver = get_ghost_driver(ghost)
    task_id = driver.make_task_id(runtime, parent_task_id)
    id_ = get_identifier(ghost)
    meta = to_entity_meta(ghost)
    task_ = GoTaskStruct.new(
        task_id=task_id,
        shell_id=runtime.shell_id,
        process_id=runtime.process_id,
        name=id_.name,
        description=id_.description,
        meta=meta,
        parent_task_id=parent_task_id
    )
    return task_
