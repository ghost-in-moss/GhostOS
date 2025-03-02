from abc import ABC, abstractmethod
from typing import Optional, Dict, Generic, TypeVar
from ghostos.core.llms import Prompt, ServiceConf
from ghostos.core.messages import Message
from ghostos_common.entity import EntityMeta, get_entity, to_entity_meta
from pydantic import BaseModel, Field


class AudioGenerationModel(BaseModel, ABC):
    name: str = Field(description="Name of the audio generator")
    driver: str = Field(description="Name of the audio generator driver")


M = TypeVar("M", bound=AudioGenerationModel)


class AudioGeneratorsConfig(BaseModel):
    default: str = Field(description="Default audio generator model")
    models: Dict[str, EntityMeta] = Field(
        default_factory=dict,
    )

    def add_model(self, model: AudioGenerationModel):
        self.models[model.name] = to_entity_meta(model)

    def get_model(self, name: str) -> Optional[AudioGenerationModel]:
        if name in self.models:
            meta = self.models[name]
            return get_entity(meta, AudioGenerationModel)
        return None


class AudioGenerationDriver(Generic[M], ABC):
    @abstractmethod
    def driver_name(self) -> str:
        pass

    @abstractmethod
    def generate(self, prompt: Prompt, conf: M) -> Message:
        pass


class AudioGenerators(ABC):

    @abstractmethod
    def register(self, generator: AudioGenerationDriver):
        pass

    @abstractmethod
    def get(self, model_name: str) -> Optional[AudioGenerationDriver]:
        pass

    @abstractmethod
    def get_model_conf(self, model_name: str) -> AudioGenerationModel:
        pass

    @abstractmethod
    def generate(self, prompt: Prompt, model: str = "") -> Message:
        pass
