from abc import ABC, abstractmethod
from typing import Iterable
from ghostos.container import INSTANCE, ABSTRACT
from ghostos.core.ghosts.actions import Action

__all__ = ['Shell']


class Shell(ABC):
    """
    Shell is the cybernetic body of the Ghost, and this interface is an abstract for the shell.
    The instance of the Shell may be changed during runtime.
    The Ghost shall feel and understand the situation of the shell, and use it.
    """

    @abstractmethod
    def id(self) -> str:
        """
        :return: identity of the shell.
        """
        pass

    @abstractmethod
    def status_description(self) -> str:
        """
        the status description of the shell, for llm ghost.
        combine this to the LLM instruction, shall prompt the LLM interact with the shell.
        """
        pass

    @abstractmethod
    def actions(self) -> Iterable[Action]:
        """
        actions from the shell
        Ghost(LLM) can interact with the shell by these actions.
        Through function call or functional token protocol.
        """
        pass

    @abstractmethod
    def drivers(self) -> Iterable[ABSTRACT]:
        """
        The drivers that this shell provided to the Ghost.
        Driver is usually a class interface, not an implementation.
        Ghost can operate the shell by generate codes in the MOSS to call these drivers.
        And the Ghost's ai models do not need to know the details of the implementation.

        The GhostOS will bind the drivers and it's implementations to the Ghost IoCContainer.

        For example, a Thought can play music by calling a driver named MusicPlayer,
        no matter the shell is a Robot, a Car, or a IM chatbot.
        """
        pass

    @abstractmethod
    def get_driver(self, driver: ABSTRACT) -> INSTANCE:
        """
        get driver's INSTANCE that already bound to the Shell.
        """
        pass
