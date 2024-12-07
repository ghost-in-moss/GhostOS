from typing import Self, Optional, Callable, List, Literal, NamedTuple, Union
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class CurveRoll(BaseModel):
    """
    to define a curve rolling frame by frame.
    """
    desc: str = Field(description="describe this curve in very few words")
    heading: int = Field(0, description="Heading angle of the sphero bolt in degrees from -180 ~ 180", ge=-180, le=180)
    speed: int = Field(90, description="speed of the sphero bolt rolling", ge=0, le=255)
    duration: float = Field(1, description="duration of the rolling, if 0, means forever")
    code: str = Field(description="the python code to change self heading, speed, stop at each frame of rolling.")

    def run_frame(self, passed: float) -> bool:
        """
        real logic of the curve rolling.
        sphero runtime will call `run_frame` method at each frame (for example: 0.01 second)
        this method shall change the speed and heading at each frame.

        :param passed: the time in seconds that passed since the curve rolling started
        :return: shall stop?
        """
        # the real logic is eval the python code here, change the heading and spead to complete a curve.
        # for example, a sin cure:
        # self.speed = 90
        # self.heading = int(math.sin(passed % 3) * 180)) % 360
        for line in self.code.splitlines():
            eval(line)
        return self.duration == 0 or passed > self.duration


class Move(ABC):
    """
    to define a sequence of sphero bolt ball movements.
    you can call several methods in order to define a sequence.
    the move instance do not execute until it is run by `Ball` interface.
    """

    @abstractmethod
    def roll(self, heading: int, speed: int, duration: float) -> Self:
        """Combines heading(0-360°), speed(-255-255), and duration to make the robot roll with one line of code.
        For example, to have the robot roll at 90°, at speed 200 for 2s, use ``roll(90, 200, 2)``"""
        pass

    @abstractmethod
    def spin(self, angle: int, duration: float) -> Self:
        """Spins the robot for a given number of degrees over time, with 360° being a single revolution.
        For example, to spin the robot 360° over 1s, use: ``spin(360, 1)``.
        Use :func:`set_speed` prior to :func:`spin` to have the robot move in circle or an arc or circle.

        Note: Unlike official API, performance of spin is guaranteed, but may be longer than the specified duration."""
        pass

    @abstractmethod
    def set_waddle(self, waddle: bool) -> Self:
        """Turns the waddle walk on using `set_waddle(True)`` and off using ``set_waddle(False)``."""
        pass

    @abstractmethod
    def roll_curve(self, curve: CurveRoll) -> Self:
        """
        run a curve rolling frame by frame until it reach the duration.
        """
        pass

    @abstractmethod
    def stop_roll(self, heading: int = None) -> Self:
        """Sets the speed to zero to stop the robot, effectively the same as the ``set_speed(0)`` command."""
        pass

    @abstractmethod
    def reset_aim(self) -> Self:
        """Resets the heading calibration (aim) angle to use the current direction of the robot as 0°."""
        pass

    @abstractmethod
    def set_compass_direction(self, direction: int = 0) -> Self:
        """
        Sets the direction relative to compass zero
        """
        pass

    # below are events methods. only need call them for certain and clear purpose.

    @abstractmethod
    def on_collision(
            self,
            log: str = "feeling collision",
            callback: Optional[Callable[[Self], None]] = None,
    ) -> None:
        """
        when the bolt feeling collision. default is stop.
        for example:
          `move.on_collision(lambda m: m.spin(180, 1))` means when collision, spin 180 degree in 1 second.
        """
        pass

    @abstractmethod
    def on_freefall(
            self,
            log: str = "feeling freefall",
            callback: Optional[Callable[[Self], None]] = None,
    ) -> None:
        """
        when the bolt feeling free fall. default is stop.
        """
        pass

    @abstractmethod
    def on_landing(
            self,
            log: str = "feeling landing",
            callback: Optional[Callable[[Self], None]] = None,
    ) -> Self:
        """
        when the bolt feeling landing. default is stop.
        """
        pass


class Ball(ABC):
    """
    Sphero bolt body (which is a rolling ball) control interface.
    """

    @abstractmethod
    def new_move(self, run_immediately: bool = False) -> Move:
        """
        create a new Move instance, to define a sequence of movements.
        :param run_immediately: run immediately if True, otherwise the move will not execute until run it.
        """
        pass

    @abstractmethod
    def run(self, move: Move, stop_at_first: bool = True) -> None:
        """
        run the bolt ball movement
        :param move: the Move instance that defined the movements by calling it methods one by one.
        :param stop_at_first: shall stop any movement of the ball before executing the new move?
        """
        pass

    @abstractmethod
    def save_move(self, name: str, description: str, move: Move) -> None:
        """
        define a move that you can call it anytime with the name only.
        **remember** only save the important move
        :param name: move name
        :param description: describe the move, in less than 100 words
        :param move: the Move instance.
        """
        pass

    @abstractmethod
    def set_matrix_rotation(self, rotation: Literal[0, 90, 180, 360] = 0) -> None:
        """
        Rotates the LED matrix
        :param rotation: 0 to 90, 180, 360 degrees
        """
        pass

    @abstractmethod
    def run_move(self, name: str) -> None:
        """
        run a defined move
        :param name: the name of the move. make sure you have run save_move() before calling it.
        :raise: NotImplementedError if move is not defined
        """
        pass

    @abstractmethod
    def on_charging(
            self,
            log: str = "feeling at charging",
    ) -> None:
        """
        when the bolt feeling start charging
        """
        pass

    @abstractmethod
    def on_not_charging(
            self,
            log: str = "feeling stop charging",
    ) -> None:
        """
        when the bolt feeling stop charging
        """
        pass


class Color(NamedTuple):
    """
    tuple of RGB colors
    """
    r: int
    g: int
    b: int


class Animation(ABC):
    """
    to define an animation by sequence of frame.
    the animation will be played on Sphero Bolt 8*8 led matrix.
    """

    @abstractmethod
    def frame(self, matrix: List[List[Union[str, Color]]]) -> Self:
        """
        define a frame of the Bolt LED matrix.
        :param matrix: 8 * 8 array, each element is either an RGB Color tuple or a defined palette color name.
        :return:
        """
        pass

    @abstractmethod
    def scroll_matrix_text(self, text: str, color_name: str, fps: int, wait: bool) -> Self:
        """
        Scrolls text on the matrix, with specified color.
        text max 25 characters
        Fps 1 to 30
        wait: if the programs wait until completion
        """
        pass

    @abstractmethod
    def set_matrix_character(self, character: str, color_name: str):
        """
        Sets a character on the matrix with color specified
        """
        pass


class LedMatrix(ABC):

    @abstractmethod
    def new_animation(self, fps: int = 1, transition: bool = True) -> Animation:
        """
        create a new animation instance, to define a sequence of frames.
        :param fps:
        :param transition:
        :return:
        """
        pass

    @abstractmethod
    def play_animation(self, animation: Animation, loop: int = 0) -> None:
        pass

    @abstractmethod
    def save_expression(self, name: str, description: str, animation: Animation) -> None:
        """
        save animation as an expression, that you can play it when every you feel it.
        """
        pass

    @abstractmethod
    def play_expression(self, name: str, loop: int = 0) -> None:
        """
        :param name: name of the defined expression animation.
        :param loop: how many times the animation is played. zero means play forever.
        """
        pass

    @abstractmethod
    def save_palette(self, color_name: str, color: Color) -> None:
        """
        save the color to the palette
        :param color_name: such as 'red', 'green', 'blue'
        :param color: RGB Color tuple
        """
        pass

    @abstractmethod
    def pause_animation(self) -> None:
        """
        pause the playing animation
        """
        pass

    @abstractmethod
    def resume_animation(self):
        """
        resume the playing animation
        """
        pass

    @abstractmethod
    def clear_matrix(self):
        """
        clear the matrix.
        """
        pass
