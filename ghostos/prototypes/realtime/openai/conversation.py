from typing import Iterable

from ghostos.prototypes.realtime.abcd import ConversationProtocol, Message


class Conversation(ConversationProtocol):

    def id(self) -> str:
        pass

    def messages(self) -> Iterable[Message]:
        pass

    def append(self, message: Message) -> None:
        pass

    def save(self):
        pass