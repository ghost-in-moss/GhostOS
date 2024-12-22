from abc import ABC, abstractmethod
from typing import Optional, List
from ghostos.ghosts.chatbot.simplest import Chatbot
from ghostos.identifier import Identifier


class Chatbots(ABC):
    @abstractmethod
    def save(self, bot: Chatbot) -> None:
        pass

    @abstractmethod
    def find(self, bot_name: str) -> Optional[Chatbot]:
        pass

    @abstractmethod
    def search(self, query: str) -> List[Identifier]:
        pass
