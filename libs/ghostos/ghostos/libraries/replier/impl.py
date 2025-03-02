from typing import Optional

from ghostos.libraries.replier.abcd import Replier
from ghostos.abcd import Session, Operator
from ghostos_container import Container, Provider, INSTANCE

__all__ = ['ReplierImpl', 'ReplierImplProvider']


class ReplierImpl(Replier):

    def __init__(self, session: Session):
        self._session = session

    def say(self, text: str) -> None:
        self._session.respond_buffer([text])

    def wait_for(self, text: str) -> Operator:
        self._session.respond_buffer([text])
        return self._session.mindflow().wait()


class ReplierImplProvider(Provider[Replier]):

    def singleton(self) -> bool:
        return False

    def factory(self, con: Container) -> Optional[INSTANCE]:
        session = con.get(Session)
        if session is None:
            raise NotImplementedError(f"{self.__class__.__name__} shall only be registered in session level container")
        return ReplierImpl(session)
