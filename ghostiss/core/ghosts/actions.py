from typing import Optional
from abc import ABC, abstractmethod
from ghostiss.container import Container
from ghostiss.core.runtime.llms import Chat
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.messenger import Messenger
from ghostiss.core.messages.message import Caller
from ghostiss.abc import Identifiable

__all__ = ['Action']


class Action(Identifiable, ABC):
    """
    ghost action that triggered by LLM output
    """

    @abstractmethod
    def update_chat(self, chat: Chat) -> Chat:
        pass

    @abstractmethod
    def act(self, container: "Container", messenger: "Messenger", caller: Caller) -> Optional["Operator"]:
        """
        """
        pass
