from typing import Iterable, List, Union, Dict, Optional
from ghostos.core.messages.message import Message, Role, MessageClass, MessageStage

__all__ = [
    'copy_messages', 'iter_messages',
]


def copy_messages(messages: Iterable[Message], stages: Optional[List[str]] = None) -> List[Message]:
    """
    syntax sugar for copy
    """
    result = []
    if stages:
        stages = set(stages)
    for message in messages:
        if MessageStage.allow(message.stage, stages):
            result.append(message.get_copy())
    return result


def iter_messages(messages: Iterable[Union[Message, str, Dict, MessageClass]]) -> Iterable[Message]:
    """
    yield from all kinds of messages
    """
    for item in messages:
        if isinstance(item, Message):
            yield item
        elif isinstance(item, str):
            yield Role.ASSISTANT.new(content=item)
        elif isinstance(item, MessageClass):
            yield item.to_message()
        elif isinstance(item, Dict):
            yield Message(**item)
        else:
            raise TypeError(f"Unexpected type {type(item)}")
