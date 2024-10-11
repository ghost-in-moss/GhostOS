from typing import List
from abc import ABC, abstractmethod
from ghostos.abc import Identifiable
from ghostos.core.llms import ChatPreparer


class User(Identifiable, ChatPreparer, ABC):

    @abstractmethod
    def allow(self, action: str, *args, **kwargs) -> bool:
        pass

    @abstractmethod
    def authorized(self, resource: str, *args, **kwargs) -> List[str]:
        pass
