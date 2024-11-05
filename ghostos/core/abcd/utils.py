from typing import TypeVar, Optional, Type
from ghostos.helpers import import_class_from_path, generate_import_path, md5
from ghostos.common import get_identifier, to_entity_meta
from .ghostos import Ghost, GhostDriver


def get_ghost_driver_type(ghost: Ghost) -> Type[GhostDriver]:
    """
    get ghost driver instance by default protocol
    """
    if ghost.__ghost_driver__ is not None:
        return ghost.__ghost_driver__
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
        id_ = get_identifier(value)
        assert id_ is not None
        meta = to_entity_meta(value)
        assert meta is not None
        driver = get_ghost_driver_type(value)
        assert issubclass(driver, GhostDriver)
        return True
    except AssertionError:
        return False


def make_ghost_task_id(
        ghost: Ghost,
        shell_id: str,
        process_id: str,
        parent_task_id: Optional[str],
) -> str:
    """
    default way to create ghost task ID
    ghost itself can be a locator to its task instance, if the task_id is the same.
    """
    identifier = get_identifier(ghost)

    # shell level id
    # if the ghost_id is generated each time, the task id is alternative
    # if the ghost_id is static, the task id is identical to shell.
    if ghost_id := identifier.id:
        unique_str = f"shell:{shell_id}:ghost_id:{ghost_id}"
        return md5(unique_str)

    # parent scope unique task
    # the task is unique to it parent by the name
    self_name = identifier.name
    cls_name = generate_import_path(ghost.__class__)
    unique_str = (f"shell:{shell_id}:process:{process_id}"
                  f":parent:{parent_task_id}:cls{cls_name}:name:{self_name}")
    return md5(unique_str)
