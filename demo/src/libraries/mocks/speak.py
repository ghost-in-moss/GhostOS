from abc import ABC, abstractmethod
from ghostos.core.session import Session


class Speak(ABC):
    """
    speak special term to user
    """

    @abstractmethod
    def say_helloworld(self):
        """
        say hello world to user
        """
        pass


class SpeakImpl(Speak):
    """
    quick test case.
    """

    def __init__(self, session: Session):
        self._session = session

    def say_helloworld(self):
        print("++++++ say helloworld")
        self._session.messenger().say("hello world!")
