from typing import Optional
from ghostiss.core.messages import Message, Role
from ghostiss.core.llms import ChatFilter, Chat


class AssistantNameFilter(ChatFilter):
    """
    调整 assistant name, 如果与当前 name 相同则去掉.
    """
    def __init__(self, name: str):
        self._name = name

    def filter(self, chat: Chat) -> Chat:
        def filter_fn(message: Message) -> Optional[Message]:
            if Role.ASSISTANT.value == message.role and message.name == self._name:
                message = message.get_copy()
            return message

        chat.filter_messages(filter_fn)
        return chat


