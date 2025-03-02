from typing import Tuple, List
from numpy import ndarray
from abc import ABC, abstractmethod


class Embeddings(ABC):

    @abstractmethod
    def get_embedding(self, lang: str, model: str = "") -> ndarray[float]:
        pass

    @abstractmethod
    def similarity(self, lang: str, compare: str, model: str = "") -> float:
        pass

    @abstractmethod
    def search(self, query: str, selections: List[str], top_k: int, threshold: float, model: str = "") -> float:
        pass
