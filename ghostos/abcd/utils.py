from typing import Optional, Type, Union, List
from types import ModuleType
from ghostos.helpers import import_class_from_path
from ghostos.identifier import get_identifier
from ghostos.entity import to_entity_meta
from ghostos.abcd.concepts import Ghost, GhostDriver, Session, Operator
from ghostos.core.runtime import Event
from ghostos.container import Provider

__all__ = [
    'get_ghost_driver', 'get_ghost_driver_type', 'is_ghost',
    'run_session_event', 'fire_session_event',
    'get_module_magic_ghost', 'get_module_magic_shell_providers',
]


def get_ghost_driver_type(ghost: Ghost) -> Type[GhostDriver]:
    """
    get ghost driver instance by default protocol
    """
    if ghost.DriverType is not None:
        return ghost.DriverType
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


def fire_session_event(session: Session, event: Event) -> Optional[Operator]:
    event, op = session.parse_event(event)
    if op is not None:
        session.logger.info("session event is intercepted and op %s is returned", op)
        return op
    if event is None:
        # if event is intercepted, stop the run.
        return None
    driver = get_ghost_driver(session.ghost)
    session.thread = session.get_truncated_thread()
    op = driver.on_event(session, event)
    # only session and driver can change event.
    return op


class InitOperator(Operator):
    def __init__(self, event: Event):
        self.event = event

    def run(self, session: Session) -> Union[Operator, None]:
        return fire_session_event(session, self.event)

    def destroy(self):
        del self.event


def run_session_event(session: Session, event: Event, max_step: int) -> None:
    op = InitOperator(event)
    step = 0
    while op is not None:
        step += 1
        if step > max_step:
            raise RuntimeError(f"Max step {max_step} reached")
        if not session.refresh(True):
            raise RuntimeError("Session refresh failed")
        session.logger.debug("start session op %s", repr(op))
        next_op = op.run(session)
        session.logger.debug("done session op %s", repr(op))
        op.destroy()
        # session do save after each op
        session.save()
        op = next_op


def get_module_magic_ghost(module: ModuleType) -> Optional[Ghost]:
    if "__ghost__" in module.__dict__:
        return module.__dict__["__ghost__"]
    return None


def __shell_providers__() -> List[Provider]:
    return []


def get_module_magic_shell_providers(module: ModuleType) -> List[Provider]:
    if __shell_providers__.__name__ in module.__dict__:
        return module.__dict__[__shell_providers__.__name__]()
    return []
