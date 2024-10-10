from typing import Iterable, List
from ghostos.core.messages.message import Message

__all__ = [
    'copy_messages',
]


def copy_messages(messages: Iterable[Message]) -> List[Message]:
    result = []
    for message in messages:
        result.append(message.model_copy(deep=True))
    return result

# seems at last not so many helper function are made....
