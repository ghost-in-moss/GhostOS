from typing import Optional, Iterable, NamedTuple, List, Tuple
from abc import ABC, abstractmethod
from ghostos.core.messages.message import Message, Payload, Attachment, Caller, Role
from ghostos.core.messages.buffers import Buffer
from ghostos.core.messages.stream import Stream
from ghostos.core.session.threads import MsgThread
from ghostos.core.llms import FunctionalToken

__all__ = ['Messenger', 'Buffed']


class Buffed(NamedTuple):
    messages: List[Message]
    """ the sent messages, all chunks are joined"""

    callers: List[Caller]
    """ the parsed callers from sent message"""


class Messenger(Stream, ABC):
    """
    Messenger is a bridge of message streams
    Messenger finish when the flush method is called.
    Each messenger can nest sub messengers, when sub messenger is finished,
    the parent messenger is not finished until the flush is called.

    why this is an abstract base class?
    there may be more abilities during streaming are needed,
    this project can only provide a basic one.
    """

    def say(self, content: str):
        """
        syntactic sugar
        """
        message = Role.ASSISTANT.new(content=content)
        self.deliver(message)

    @abstractmethod
    def flush(self) -> Tuple[List[Message], List[Caller]]:
        """
        flush the buffed messages, finish the streaming of this messenger.
        the message buffer shall join all the chunks to message item.
        after the messenger is flushed, it can not send any new message.
        """
        pass
