from typing import List, Iterable
from abc import ABC, abstractmethod
from ghostiss.core.messages.message import Message
from ghostiss.core.messages.attachments import Attachment
from ghostiss.core.messages.deliver import Deliver, Buffed

__all__ = ['Messenger']


class Messenger(Deliver, ABC):
    """
    向下游发包的封装.
    """

    pass

