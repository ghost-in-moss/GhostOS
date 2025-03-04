from typing import List, Optional
from abc import ABC, abstractmethod
from ghostos.abcd import Operator
from ghostos_common.prompter import POM


class Reasoning(ABC):
    """
    thinking library that help agent think through.
    """

    @abstractmethod
    def reasoning(self, instruction: str) -> Operator:
        """
        let yourself reason on the instruction before action,
        then you can make decision based on the reasoning.
        """
        pass

    @abstractmethod
    def async_reasoning(self, instruction: str = "") -> Operator:
        """
        asynchronous reasoning, you will get the result later.
        you shall reply user first about you are thinking deeper.
        """
        pass


class GetSuggestion(POM, ABC):
    """
    get suggestion from other models.
    """

    @abstractmethod
    def get_suggestions(self, context: str, quest: str, models: Optional[List[str]] = None) -> Operator:
        """
        get suggestion from other models.
        :param context: the context of the quest
        :param quest: describe what  suggestions you want from the models.
        :param models: if None, you will get suggestion from yourself model.
        """
        pass

    @abstractmethod
    def async_get_suggestions(self, context: str, quest: str, models: Optional[List[str]] = None) -> Operator:
        """
        just like the method `get_suggestions`, but you will get suggestion asynchronously.
        """
        pass


class Planner(POM, ABC):

    @abstractmethod
    def new_plan(self):
        pass
