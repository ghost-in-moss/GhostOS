from typing import Iterable, List
from ghostiss.core.messages.message import Message

__all__ = [
    'copy_messages',
]


def copy_messages(messages: Iterable[Message]) -> List[Message]:
    result = []
    for message in messages:
        result.append(message.model_copy())
    return result
