from abc import ABC
from .transport import Message, Delivery, Item, UpStream

__all__ = ['Message', 'MessageDelivery', 'MessageStream', 'MessagePack']


class MessageItem(Item, ABC):
    pass


class MessagePack(Message, ABC):
    pass


class MessageDelivery(Delivery, ABC):
    pass


class MessageStream(UpStream, ABC):
    pass
