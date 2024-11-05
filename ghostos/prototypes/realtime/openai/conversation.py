from typing import Iterable, List, Dict
from abc import ABC, abstractmethod

from ghostos.prototypes.realtime.abcd import ConversationProtocol
from ghostos.core.messages import Message


class AbsConversation(ConversationProtocol, ABC):
    message_index: Dict[int, str]
    message_map: Dict[str, Message]

    def __init__(
            self,
            message_index: Dict[int, str],
            message_map: Dict[str, Message],
    ):
        self.message_index = message_index
        self.message_map = message_map

    def messages(self) -> List[Message]:
        keys = self.message_index.keys()
        sorted_keys = sorted(keys)
        messages = []
        for index in sorted_keys:
            msg_id = self.message_index[index]
            message = self.message_map.get(msg_id)
            messages.append(message)
        return messages

    def add(self, message: Message) -> None:
        msg_id = message.msg_id
        index = message.index
        if index is not None:
            self.message_index[index] = msg_id
        self.message_map[msg_id] = message
        self.save()

    @abstractmethod
    def save(self):
        pass
