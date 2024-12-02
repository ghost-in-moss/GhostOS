from typing import Union
from ghostos.core.messages import Message
from .event_from_server import ClientEvent

__all__ = ['parse_message_to_client_event', 'parse_server_event_to_message']


def parse_message_to_client_event(message: Message) -> Union[ClientEvent, None]:
    # raise NotImplementedError("todo")
    return None


def parse_server_event_to_message(event: dict) -> Union[Message, None]:
    # raise NotImplementedError("todo")
    return None
