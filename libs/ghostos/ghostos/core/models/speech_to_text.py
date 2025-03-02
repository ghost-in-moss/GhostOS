from abc import ABC, abstractmethod
from ghostos.contracts.assets import FileInfo
from ghostos.core.messages import Message


class SpeechToTextDriver(ABC):
    pass


class SpeechToText(ABC):

    @abstractmethod
    def transcript(self, file: FileInfo, model: str = "") -> Message:
        pass
