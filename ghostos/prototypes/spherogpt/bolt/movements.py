from typing import List, Union, Dict, Optional, Self
from spherov2.sphero_edu import SpheroEduAPI
from pydantic import BaseModel, Field
from ghostos.entity import ModelEntityMeta, to_entity_model_meta, from_entity_model_meta

from .runtime import BoltBallMovement
from .shell import CurveRoll


class RunAPIMovement(BoltBallMovement):
    desc: str = Field(description="desc of the movement")
    method: str = Field(description="sphero edu api name")
    args: List[Union[str, int, float]] = Field(default_factory=list, description="args")
    kwargs: Dict[str, Union[str, int, float]] = Field(default_factory=dict, description="kwargs")
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
    curve: CurveRoll = Field(description="curve roll")
    stopped: bool = Field(default=False)
    error: str = Field("")

    def start(self, api: SpheroEduAPI) -> None:
        self.run_frame(api, 0)

    def run_frame(self, api: SpheroEduAPI, passed: float) -> bool:
        try:
            self.stopped = self.curve.run_frame(passed)
        except Exception as e:
            self.error = str(e)
            return False
        api.set_speed(self.curve.speed)
        api.set_heading(self.curve.heading)
        return self.stopped

    def on_event(self, event_type: str) -> Optional[Self]:
        return None


class GroupMovement(BoltBallMovement):
    children: List[ModelEntityMeta] = Field(default_factory=list)
    iter_idx: int = Field(default=0)
    new_child_start_at: float = Field(default=0.0)
    event_desc: Optional[str] = Field(default=None)
    event_moves: Dict[str, ModelEntityMeta] = Field(default_factory=dict)

    def add_child(self, move: BoltBallMovement):
        meta = to_entity_model_meta(move)
        self.children.append(meta)

    def get_child(self, idx: int) -> BoltBallMovement:
        meta = self.children[idx]
        return from_entity_model_meta(meta)

    def start(self, api: SpheroEduAPI) -> None:
        if len(self.children) > 0:
            self.iter_idx = 0
            child = self.get_child(self.iter_idx)
            child.start(api)

    def run_frame(self, api: SpheroEduAPI, passed: float) -> bool:
        if self.iter_idx >= len(self.children):
            return False
        child = self.get_child(self.iter_idx)
        child_passed = passed - self.new_child_start_at
        stopped = child.run_frame(api, child_passed)
        if stopped:
            self.iter_idx += 1
            self.new_child_start_at = passed
            return self.run_frame(api, passed)
        return False

    def on_event(self, event_type: str) -> Optional[Self]:
        if event_type in self.event_moves:
            meta = self.event_moves[event_type]
            return from_entity_model_meta(meta)
        return None
