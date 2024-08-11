from typing import TypeVar, Generic
from abc import ABC, abstractmethod
from pydantic import BaseModel
from ghostiss.core.messages import Message
from ghostiss.core.llms.chat import Chat

R = TypeVar("R")


class Quest(BaseModel, Generic[R], ABC):

    @abstractmethod
    def to_chat(self) -> Chat:
        pass

    @abstractmethod
    def on_result(self, msg: Message) -> R:
        pass
