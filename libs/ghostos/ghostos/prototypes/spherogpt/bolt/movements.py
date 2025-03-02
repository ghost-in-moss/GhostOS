from typing import List, Union, Dict, Optional
from typing_extensions import Self
from pydantic import BaseModel, Field
from ghostos_common.entity import ModelEntityMeta, to_entity_model_meta, from_entity_model_meta

from .runtime import BoltBallMovement
from .sphero_edu_api_patch import SpheroEduAPI
from .bolt_shell import RollFunc, Animation


class RunAPIMovement(BoltBallMovement):
    desc: str = Field(description="desc of the movement")
    method: str = Field(description="sphero edu api name")
    args: List[Union[str, int, float, None]] = Field(default_factory=list, description="args")
    kwargs: Dict[str, Union[str, int, float, None]] = Field(default_factory=dict, description="kwargs")
    duration: float = Field(0.0, description="duration of the movement")

    def start(self, api: SpheroEduAPI) -> None:
        method = getattr(api, self.method)
        method(*self.args, **self.kwargs)

    def run_frame(self, api: SpheroEduAPI, passed: float) -> bool:
        return passed > self.duration

    def on_event(self, event_type: str) -> Optional[Self]:
        return None


class CurveRollMovement(BoltBallMovement):
    desc: str = Field(description="desc of the movement")
    curve: RollFunc = Field(description="curve roll")
    stopped: bool = Field(default=False)
    error: str = Field("")

    def start(self, api: SpheroEduAPI) -> None:
        self.run_frame(api, 0)

    def run_frame(self, api: SpheroEduAPI, passed: float) -> bool:
        self.stopped = self.curve.run_frame(passed)
        if not self.stopped:
            api.set_speed(self.curve.speed)
            api.set_heading(self.curve.heading)
        return self.stopped

    def on_event(self, event_type: str) -> Optional[Self]:
        return None


class GroupMovement(BoltBallMovement):
    animation: Optional[Animation] = Field(None)
    children: List[ModelEntityMeta] = Field(default_factory=list)
    event_desc: Optional[str] = Field(default=None)
    event_moves: Dict[str, ModelEntityMeta] = Field(default_factory=dict)
    __iter_idx__: int = 0
    __new_child_started__: bool = False
    __new_child_start_at__: float = 0.0

    def add_child(self, move: BoltBallMovement):
        meta = to_entity_model_meta(move)
        self.children.append(meta)

    def get_child(self, idx: int) -> BoltBallMovement:
        meta = self.children[idx]
        return from_entity_model_meta(meta)

    def start(self, api: SpheroEduAPI) -> None:
        if len(self.children) > 0:
            self.__iter_idx__ = 0
            child = self.get_child(self.__iter_idx__)
            child.start(api)
            self.__new_child_started__ = True

    def run_frame(self, api: SpheroEduAPI, passed: float) -> bool:
        if self.__iter_idx__ >= len(self.children):
            return True
        child = self.get_child(self.__iter_idx__)
        # start if not started
        if not self.__new_child_started__:
            child.start(api)
            self.__new_child_started__ = True

        child_passed = passed - self.__new_child_start_at__
        stopped = child.run_frame(api, child_passed)
        if stopped:
            self.__iter_idx__ += 1
            self.__new_child_start_at__ = passed
            self.__new_child_started__ = False
            return self.run_frame(api, passed)
        return False

    def on_event(self, event_type: str) -> Optional[Self]:
        if event_type in self.event_moves:
            meta = self.event_moves[event_type]
            return from_entity_model_meta(meta)
        return None

    def add_event_move(self, event_type: str, move: BoltBallMovement):
        self.event_moves[event_type] = to_entity_model_meta(move)
