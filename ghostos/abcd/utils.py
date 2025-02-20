from typing import Optional, Type, Union, List
from types import ModuleType
from ghostos_common.helpers import import_class_from_path
from ghostos_common.identifier import get_identifier, Identifier
from ghostos_common.entity import to_entity_meta
from ghostos.abcd.concepts import Ghost, GhostDriver, Session, Operator
from ghostos.core.runtime import Event
from ghostos_container import Provider

__all__ = [
    'get_ghost_driver', 'get_ghost_driver_type', 'is_ghost',
    'get_ghost_identifier',
    'default_init_event_operator',
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
    if not ghost_driver_type or not issubclass(ghost_driver_type, GhostDriver):
        raise NotImplementedError(f"the Ghost {type(ghost)} has no ghost driver type")
    return ghost_driver_type(ghost)


def get_ghost_identifier(ghost: Ghost) -> Identifier:
    """
    syntax sugar
    """
    return get_identifier(ghost)


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
    except AttributeError:
        return False


class InitOperator(Operator):
    def __init__(self, event: Event):
        self.event = event

    def run(self, session: Session) -> Union[Operator, None]:
        return session.handle_event(self.event)

    def destroy(self):
        del self.event


def default_init_event_operator(event: Event) -> Operator:
    return InitOperator(event)


def get_module_magic_ghost(module: ModuleType) -> Optional[Ghost]:
    if "__ghost__" in module.__dict__:
        return module.__dict__["__ghost__"]
    return None


def __shell_providers__() -> List[Provider]:
    """
    magic method to define shell level providers in a target python file.
    """
    return []


def get_module_magic_shell_providers(module: ModuleType) -> List[Provider]:
    if __shell_providers__.__name__ in module.__dict__:
        fn = module.__dict__[__shell_providers__.__name__]
        providers = list(fn())
        return providers
    return []
