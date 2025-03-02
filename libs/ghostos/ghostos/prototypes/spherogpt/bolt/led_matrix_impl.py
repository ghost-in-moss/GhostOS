from typing import List, Dict, Optional, AnyStr
from typing_extensions import Self

from .sphero_edu_api_patch import SpheroEduAPI

from ghostos.prototypes.spherogpt.bolt.bolt_shell import LedMatrix, Animation
from ghostos.prototypes.spherogpt.bolt.runtime import BoltLedMatrixCommand, SpheroBoltRuntime
from ghostos.prototypes.spherogpt.bolt.sphero_edu_api_patch import Color
from ghostos_container import Container, Provider
from pydantic import BaseModel, Field


def parse_str_to_color(s: AnyStr) -> Color:
    color = str(s).lower()
    if not color.startswith("0x"):
        color = "0x" + color
    digits = int(color, 0)
    return Color(digits >> 16, (digits >> 8) % 256, digits % 256)


class AnimationMemoryCache(BaseModel):
    palette: Dict[str, List[int]] = Field(default_factory=dict, description="Palette of colors. name to (r, g, b)")

    def add_palette(self, name: str, color: Color):
        self.palette[name] = [color.r, color.g, color.b]


class ResumeAnimation(BoltLedMatrixCommand):

    def start(self, api: SpheroEduAPI) -> None:
        api.resume_matrix_animation()


class ClearMatrix(BoltLedMatrixCommand):

    def start(self, api: SpheroEduAPI) -> None:
        api.clear_matrix()


class PauseAnimation(BoltLedMatrixCommand):

    def start(self, api: SpheroEduAPI) -> None:
        api.pause_matrix_animation()


class ScrollMatrixText(BoltLedMatrixCommand):
    text: str = Field(description="the outputting text")
    color: str = Field(default="ffffff", description="the palette color of the text")
    fps: int = Field(default=1, description="the fps of the animation")
    wait: bool = Field(default=True, description="wait for the animation to finish")

    def start(self, api: SpheroEduAPI) -> None:
        rgb = parse_str_to_color(str(self.color))
        api.scroll_matrix_text(self.text, rgb, self.fps, self.wait)


class SetMatrixChar(BoltLedMatrixCommand):
    character: str = Field(description="the charactor")
    color: str = Field(default="ffffff", description="the palette color of the text")

    def start(self, api: SpheroEduAPI) -> None:
        color = parse_str_to_color(self.color)
        api.set_matrix_character(self.character, color)


class PlayAnimation(BoltLedMatrixCommand):
    animation: Animation

    def start(self, api: SpheroEduAPI) -> None:
        frames = self.animation.frames
        fps = int(self.animation.fps)
        palette = []
        for color in self.animation.palette:
            rgb = parse_str_to_color(color)
            palette.append(rgb)

        api.register_matrix_animation(
            frames,
            fps=fps,
            palette=palette,
            transition=bool(self.animation.transition),
        )
        aid = api.get_animation_id()
        api.play_matrix_animation(aid, self.animation.loop)

    def end(self, api: SpheroEduAPI, passed: float) -> bool:
        duration = self.animation.duration
        if 0 < duration <= passed:
            api.clear_matrix()
            return True
        return False


class LedMatrixImpl(LedMatrix):

    def __init__(self, runtime: SpheroBoltRuntime):
        self._runtime = runtime
        self.last_command: Optional[BoltLedMatrixCommand] = None

    def _add_command(self, command: BoltLedMatrixCommand):
        self._runtime.add_matrix_command(command)
        self.last_command = command

    def play_animation(self, animation: Animation) -> None:
        pa = PlayAnimation(animation=animation)
        self._runtime.add_matrix_command(pa)

    def scroll_matrix_text(self, text: str, color: str = 'ffffff', fps: int = 1, wait: bool = True) -> Self:
        if len(text) > 25:
            raise AttributeError("Text length must be less than 25 characters")
        for char in text:
            if ord(char) > 255:
                raise AttributeError("Character must be in range(0, 256)")

        s = ScrollMatrixText(text=text, color_name=color, fps=fps, wait=wait)
        self._add_command(s)
        return self

    def set_matrix_character(self, character: str, color: str):
        s = SetMatrixChar(character=character, color=color)
        self._add_command(s)

    def pause_animation(self) -> None:
        self._add_command(PauseAnimation())

    def resume_animation(self):
        self._add_command(ResumeAnimation())

    def clear_matrix(self):
        self._add_command(ClearMatrix())


class SpheroBoltLedMatrixProvider(Provider[LedMatrix]):

    def singleton(self) -> bool:
        return False

    def factory(self, con: Container) -> Optional[LedMatrix]:
        runtime = con.force_fetch(SpheroBoltRuntime)
        return LedMatrixImpl(
            runtime=runtime,
        )
