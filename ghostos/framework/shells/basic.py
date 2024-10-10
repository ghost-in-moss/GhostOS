from typing import Type, Iterable, List, Tuple

from ghostos.container import INSTANCE, ABSTRACT
from ghostos.core.ghosts import Action
from ghostos.core.ghosts.shells import Shell


class BasicShell(Shell):
    """
    A shell implementation that almost do nothing important.
    just for testing.
    """

    def __init__(
            self, *,
            shell_id: str,
            prompt: str,
            actions: List[Action],
            drivers: List[Tuple[Type, object]]
    ):
        self._id = shell_id
        self._actions = actions
        self._prompt = prompt
        self._drivers = {t: i for t, i in drivers}

    def id(self) -> str:
        return self._id

    def status_description(self) -> str:
        return self._prompt

    def actions(self) -> Iterable[Action]:
        return self._actions

    def drivers(self) -> Iterable[ABSTRACT]:
        for driver in self._drivers:
            yield driver

    def get_driver(self, driver: ABSTRACT) -> INSTANCE:
        if driver not in self._drivers:
            raise KeyError(f"Driver {driver} not supported")
        return self._drivers[driver]
