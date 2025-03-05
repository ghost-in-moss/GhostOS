from typing import Optional, Callable, Dict, Tuple
from typing_extensions import Self, Literal

from spherov2.commands.io import FrameRotationOptions

from ghostos.contracts.storage import FileStorage
from ghostos.contracts.workspace import Workspace
from ghostos.abcd import Conversation
from ghostos_common.entity import ModelEntityMeta, from_entity_model_meta, to_entity_model_meta
from ghostos_common.helpers import yaml_pretty_dump
from ghostos_common.prompter import PromptObjectModel
from ghostos_container import Container, Provider
from ghostos_moss import Injection, MossRuntime
from pydantic import BaseModel, Field
from ghostos.prototypes.spherogpt.bolt.sphero_edu_api_patch import SpheroEventType
from ghostos.prototypes.spherogpt.bolt.bolt_shell import Ball, Move, RollFunc, Animation
from ghostos.prototypes.spherogpt.bolt.runtime import SpheroBoltRuntime, BoltBallMovement
from ghostos.prototypes.spherogpt.bolt.movements import (
    GroupMovement,
    RunAPIMovement,
    CurveRollMovement,
)
import yaml

__all__ = ['SpheroBoltBallAPIProvider', 'BallImpl']


class SavedMove(BaseModel):
    name: str = Field(description="move name")
    description: str = Field(description="move description")
    move_meta: ModelEntityMeta = Field(description="move meta")
    generated_code: str = Field(default="", description="the code creating this move")

    @classmethod
    def new(cls, name: str, description: str, move: BoltBallMovement) -> Self:
        return SavedMove(
            name=name,
            description=description,
            move_meta=to_entity_model_meta(move),
        )

    def get_move(self) -> BoltBallMovement:
        return from_entity_model_meta(self.move_meta)


class MovesMemoryCache(BaseModel):
    moves: Dict[str, SavedMove] = Field(default_factory=dict)

    def add_saved(self, saved: SavedMove):
        self.moves[saved.name] = saved

    def get_move(self, name: str) -> Optional[BoltBallMovement]:
        got = self.moves.get(name, None)
        if got is None:
            return None
        return from_entity_model_meta(got.move_meta)

    @staticmethod
    def filename(unique_id: str) -> str:
        return f"{unique_id}_sphero_moves.yml"

    def to_content(self) -> str:
        return yaml_pretty_dump(self.model_dump())


class MoveAdapter(Move):

    def __init__(
            self,
            runtime: SpheroBoltRuntime,
            run_immediately: bool,
            animation: Optional[Animation] = None,
            event_desc: str = "",
            buffer: Optional[GroupMovement] = None,
    ):
        self._runtime = runtime
        self._run_immediately = run_immediately
        self._move_added: int = 0
        if buffer is None:
            buffer = GroupMovement(desc="move", event_desc=event_desc or "", animation=animation)
        if animation is not None:
            buffer.animation = animation
        self.buffer: GroupMovement = buffer

    def _add_move(self, movement: BoltBallMovement):
        if self._run_immediately:
            movement.stop_at_first = self._move_added == 0
            self._runtime.add_movement(movement)

        self.buffer.add_child(movement)
        self._move_added += 1

    def roll(self, heading: int, speed: int, duration: float) -> Self:
        roll_fn = RollFunc(
            heading=heading,
            speed=speed,
            duration=duration,
            code="",
        )
        move = CurveRollMovement(
            desc="roll",
            curve=roll_fn,
        )
        self._add_move(move)
        return self

    def spin(self, angle: int, duration: float) -> Self:
        self._add_move(RunAPIMovement(
            desc="spin",
            method="spin",
            duration=duration,
            args=[angle, duration],
        ))
        return self

    def set_waddle(self, waddle: bool) -> Self:
        self._add_move(RunAPIMovement(
            desc="set_waddle",
            method="set_waddle",
            duration=0.0,
            args=[waddle],
        ))
        return self

    def roll_by_func(self, fn: RollFunc) -> Self:
        self._add_move(CurveRollMovement(
            desc="roll_curve",
            curve=fn,
        ))
        return self

    def stop_roll(self, heading: int = None) -> Self:
        self._add_move(RunAPIMovement(
            desc="stop_roll",
            method="stop_roll",
            duration=0.0,
            args=[heading],
        ))
        return self

    def reset_aim(self) -> Self:
        self._add_move(RunAPIMovement(
            desc="reset_aim",
            method="reset_aim",
            duration=0.0,
            args=[],
        ))
        return self

    def set_compass_direction(self, direction: int = 0) -> Self:
        self._add_move(RunAPIMovement(
            desc="reset_aim",
            method="reset_aim",
            duration=0.0,
            args=[],
        ))
        return self

    def on_collision(
            self,
            callback: Optional[Callable[[Self], None]] = None,
            *,
            log: str = "feeling collision",
    ) -> None:
        self._add_event_callback(SpheroEventType.on_collision.name, log, callback)

    def _add_event_callback(
            self,
            event_name: str,
            log: str,
            callback: Optional[Callable[[Self], None]] = None,
    ) -> None:
        sub_move = MoveAdapter(
            runtime=self._runtime,
            run_immediately=False,
            event_desc=log,
        )
        if callback is not None:
            callback(sub_move)
        event_move = sub_move.buffer
        event_move.stop_at_first = True
        self.buffer.add_event_move(event_name, event_move)

    def on_freefall(
            self,
            log: str = "feeling freefall",
            *,
            callback: Optional[Callable[[Self], None]] = None,
    ) -> None:
        self._add_event_callback(SpheroEventType.on_freefall.name, log, callback)

    def on_landing(
            self,
            callback: Optional[Callable[[Self], None]] = None,
            *,
            log: str = "feeling landing",
    ) -> None:
        self._add_event_callback(SpheroEventType.on_landing.name, log, callback)


class BallImpl(Ball, Injection, PromptObjectModel):

    def __init__(
            self,
            runtime: SpheroBoltRuntime,
            memory_cache: FileStorage,
            executing_code: Optional[str] = None,
    ):
        self._runtime = runtime
        self._executing_code = executing_code
        self._memory_cache_storage = memory_cache
        self._memory_cache_file = MovesMemoryCache.filename(self._runtime.get_task_id())
        if self._memory_cache_storage.exists(self._memory_cache_file):
            content = self._memory_cache_storage.get(self._memory_cache_file)
            data = yaml.safe_load(content)
            self._memory_cache = MovesMemoryCache(**data)
        else:
            self._memory_cache = MovesMemoryCache()

    def _save_cache(self):
        content = self._memory_cache.to_content()
        self._memory_cache_storage.put(self._memory_cache_file, content.encode())

    def on_inject(self, runtime: MossRuntime, property_name: str) -> Self:
        self._executing_code = runtime.moss().executing_code
        return self

    def on_destroy(self) -> None:
        return None

    def new_move(
            self,
            *,
            animation: Optional[Animation] = None,
            run: bool = False,
    ) -> Move:
        return MoveAdapter(self._runtime, run, animation=animation)

    def run(self, move: Move, stop_at_first: bool = True) -> None:
        if not isinstance(move, MoveAdapter):
            raise TypeError(f"move instance must be created by this api new_move()")
        movement = move.buffer
        if movement.animation is not None:
            self._runtime.add_animation(movement.animation)
        movement.stop_at_first = stop_at_first
        self._runtime.add_movement(movement)

    def save_move(self, name: str, description: str, move: Move, animation: Optional[Animation] = None) -> None:
        if not isinstance(move, MoveAdapter):
            raise TypeError(f"move instance must be created by this api new_move()")
        if animation:
            move.buffer.animation = animation
        saved_move = SavedMove.new(name=name, description=description, move=move.buffer)
        saved_move.generated_code = self._executing_code or ""
        self._memory_cache.add_saved(saved_move)
        self._save_cache()

    def delete_move(self, name: str) -> None:
        if name in self._memory_cache.moves:
            del self._memory_cache.moves[name]
            self._save_cache()

    def set_matrix_rotation(self, rotation: Literal[0, 90, 180, 270] = 0) -> None:
        rotations = {
            0: FrameRotationOptions.NORMAL,
            90: FrameRotationOptions.ROTATE_90_DEGREES,
            180: FrameRotationOptions.ROTATE_180_DEGREES,
            270: FrameRotationOptions.ROTATE_270_DEGREES,
        }
        move = RunAPIMovement(
            desc="set_matrix_rotation",
            method="set_matrix_rotation",
            args=[rotations.get(rotation, FrameRotationOptions.NORMAL)]
        )
        self._runtime.add_movement(move)

    def run_move(self, name: str) -> None:
        got = self._memory_cache.get_move(name)
        if got is None:
            raise NotImplementedError(f"move {name} not implemented")
        got.stop_at_first = True
        self._runtime.add_movement(got)

    def read_move(self, name: str) -> Tuple[Move, str]:
        saved = self._memory_cache.moves.get(name, None)
        if saved is None:
            raise NotImplementedError(f"move {name} not implemented")
        got = self._memory_cache.get_move(name)
        move = MoveAdapter(
            self._runtime,
            run_immediately=False,
            buffer=got,
        )
        return move, saved.generated_code

    def on_charging(self, log: str = "feeling at charging") -> None:
        self._runtime.set_charging_callback(log)

    def on_not_charging(self, log: str = "feeling stop charging") -> None:
        self._runtime.set_off_charging_callback(log)

    def self_prompt(self, container: Container) -> str:
        if len(self._memory_cache.moves) == 0:
            return ""
        lines = []
        for move in self._memory_cache.moves.values():
            line = f"- `{move.name}`: {move.description}"
            lines.append(line)
        saved_content = "\n".join(lines)
        return f"""
your saved moves, from name to description are below:
{saved_content}

you can run the saved move by it's name.
"""

    def get_title(self) -> str:
        return "SpheroBolt Ball saved moves"


class SpheroBoltBallAPIProvider(Provider[Ball]):

    def singleton(self) -> bool:
        return False

    def factory(self, con: Container) -> Optional[Ball]:
        runtime = con.force_fetch(SpheroBoltRuntime)
        workspace = con.force_fetch(Workspace)
        conversation = con.force_fetch(Conversation)
        runtime.connect(conversation.task_id, False)
        return BallImpl(runtime, workspace.runtime_cache())
