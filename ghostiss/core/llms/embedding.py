from typing import List, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


# ---- config ---- #

class Embedding(BaseModel):
    content: str = Field(description="origin content")
    service: str = Field(description="llm service")
    model: str = Field(description="llm model")
    embedding: List[float] = Field(description="embedding")


class Embeddings(BaseModel):
    result: List[Embedding] = Field(default_factory=list)
    # todo: 未来再管这些.
    # cast: Cast = Field(description="cast")


class EmbedApi(ABC):

    @abstractmethod
    def get_embedding(self, content: str, model: Optional[str] = None) -> Embedding:
        pass

    @abstractmethod
    def get_embeddings(self, contents: List[str], model: Optional[str] = None) -> Embeddings:
        pass
