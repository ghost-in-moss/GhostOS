from typing import Optional, Type
from .ghostos_for_ai import Task, State, Moss
from .ghostos_for_user import Agent
from .kernel import Ghost, Shell

__task__: Optional[Type[Task]] = None
__state__: Optional[Type[State]] = None
__moss__: Optional[Type[Moss]] = None
__agent__: Optional[Agent] = None
__ghost__: Optional[Ghost] = None
__shell__: Optional[Shell] = None
