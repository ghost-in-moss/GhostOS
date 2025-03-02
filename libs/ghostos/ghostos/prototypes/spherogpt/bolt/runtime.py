from abc import ABC, abstractmethod
from typing import Optional
from typing_extensions import Self
from ghostos_common.entity import ModelEntity
from pydantic import BaseModel, Field
from .sphero_edu_api_patch import SpheroEduAPI

from ghostos.prototypes.spherogpt.bolt.bolt_shell import Animation

_STOPPED = bool


class BoltBallMovement(BaseModel, ABC):
    animation: Optional[Animation] = Field(None)
    desc: str = Field("", description="description of the command")
    stop_at_first: bool = Field(default=False, description="stop the world at first")

    @abstractmethod
    def start(self, api: SpheroEduAPI) -> None:
        pass

    @abstractmethod
    def run_frame(self, api: SpheroEduAPI, passed: float) -> _STOPPED:
        pass

    def succeed_log(self, passed: float) -> str:
        if not self.desc:
            return ""
        return f"done `{self.desc}` after {round(passed, 4)} seconds"

    def interrupt_log(self, reason: str, passed: float) -> str:
        desc = self.desc or str(type(self))
        return f"interrupt `{desc}` running because `{reason}` after {round(passed, 4)} seconds"

    @abstractmethod
    def on_event(self, event_type: str) -> Optional[Self]:
        pass


class BoltLedMatrixCommand(ModelEntity, ABC):

    @abstractmethod
    def start(self, api: SpheroEduAPI) -> None:
        pass

    def end(self, api: SpheroEduAPI, passed: float) -> bool:
        return True


class SpheroBoltRuntime(ABC):

    @abstractmethod
    def get_task_id(self) -> str:
        pass

    @abstractmethod
    def connect(self, task_id: str, shall_notify: bool):
        pass

    @abstractmethod
    def add_movement(self, command: BoltBallMovement):
        pass

    @abstractmethod
    def add_animation(self, animation: Animation) -> None:
        pass

    @abstractmethod
    def set_charging_callback(self, event: str):
        pass

    @abstractmethod
    def set_off_charging_callback(self, event: str):
        pass

    @abstractmethod
    def add_matrix_command(self, command: BoltLedMatrixCommand):
        pass

    @abstractmethod
    def bootstrap(self):
        pass

    @abstractmethod
    def close(self):
        pass
