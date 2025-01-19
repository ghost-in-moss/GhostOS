from typing import Optional, Callable, List, Literal, Tuple
from typing_extensions import Self
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class RollFunc(BaseModel):
    """
    to define a curve rolling frame by frame.
    """
    heading: int = Field(0, description="Heading angle of the sphero bolt in degrees from -180 ~ 180", ge=-360, le=360)
    speed: int = Field(90, description="speed of the sphero bolt rolling", ge=0, le=255)
    duration: float = Field(1, description="duration of the rolling, if 0, means forever")
    code: str = Field(
        default="",
        description="the python code to change self heading, speed, stop at each frame of rolling."
                    "if empty, means run straight",
    )

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
        if self.code:
            code = "\n".join([line.lstrip() for line in self.code.splitlines()])
            exec(code)
        return not (self.duration == 0 or passed < self.duration)


class Straight(RollFunc):
    heading: int = Field(0)
    speed: int = Field(90)
    duration: float = Field(1)
    code: str = ""

    def run_frame(self, passed: float) -> bool:
        return not (self.duration == 0 or passed < self.duration)


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
    def roll_by_func(self, fn: RollFunc) -> Self:
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
            callback: Optional[Callable[[Self], None]] = None,
    ) -> None:
        """
        when the bolt feeling free fall. default is stop.
        """
        pass

    @abstractmethod
    def on_landing(
            self,
            callback: Optional[Callable[[Self], None]] = None,
    ) -> None:
        """
        when the bolt feeling landing. default is stop.
        """
        pass


class Animation(BaseModel):
    """
    to define an animation by sequence of frame.
    the animation will be played on Sphero Bolt 8*8 led matrix.
    """
    fps: int = Field(1, description="frames per second", ge=1, le=30),
    transition: bool = Field(True, description="if true, fade between frames"),
    palette: List[str] = Field(
        default_factory=lambda: ["000000", "ff0000", "00ff00", "0000ff", "ffffff"],
        description="define color palette, the index is the color id. "
                    "in default case: 0 is black, 1 is red, 2 is green, 3 is blue, 4 is white",
    ),
    loop: bool = Field(
        default=True,
        description="loop count for animation",
    ),
    duration: float = Field(default=0.0, description="duration of animation in seconds, clear matrix after animation"),
    frames: List[List[List[int]]] = Field(
        default_factory=lambda: [
            [
                # a simple smile
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 1, 1, 0, 0, 1, 1, 0],
                [1, 0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 1, 0],
                [0, 0, 1, 1, 1, 1, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
            ]
        ],
        description="list of animation frame, every frame is a 8*8 matrix, each element is an palette color index",
    )

    def add_frame(self, frame: List[List[int]]) -> None:
        self.frames.append(frame)

    def add_frame_by_node(
            self,
            nodes: List[Tuple[int, int, int]],
            background_color: int = 0,
    ):
        """
        add a frame by declare several nodes only.
        :param nodes: list of nodes. [(row, col, color), ...]
        :param background_color: color index from palette
        """
        row = [background_color] * 8
        frame = [row] * 8  # create an empty
        for node in nodes:
            row_idx, col_idx, color_idx = node
            target_row = frame[row_idx]
            target_row[col_idx] = color_idx
        self.add_frame(frame)


class Ball(ABC):
    """
    Sphero bolt body (which is a rolling ball) control interface.
    """

    @abstractmethod
    def new_move(
            self,
            *,
            run: bool = False,
            animation: Optional[Animation] = None,
    ) -> Move:
        """
        create a new Move instance, to define a sequence of movements.
        :param run: run immediately if True, otherwise the move will not execute until run it.
        :param animation: if animation is not none, it will be played while run the move.
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
    def save_move(self, name: str, description: str, move: Move, animation: Optional[Animation] = None) -> None:
        """
        define a move that you can call it anytime with the name only.
        **remember** only save the important one
        :param name: move name
        :param description: describe the move, in less than 100 words
        :param move: the Move instance.
        :param animation: if animation is not none, it will be played while run the move.
        """
        pass

    @abstractmethod
    def read_move(self, name: str) -> Tuple[Move, str]:
        """
        read a saved move with the code that generated it.
        print the code to see details.
        :param name: move name
        :return: (move instance, the code that generated it.)
        """
        pass

    @abstractmethod
    def delete_move(self, name: str) -> None:
        """
        delete move by name
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
    def set_matrix_rotation(self, rotation: Literal[0, 90, 180, 360] = 0) -> None:
        """
        Rotates the LED matrix
        :param rotation: 0 to 90, 180, 360 degrees
        """
        pass


class LedMatrix(ABC):

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

    @abstractmethod
    def scroll_matrix_text(self, text: str, color: str = 'ffffff', fps: int = 1, wait: bool = True) -> Self:
        """
        Scrolls text on the matrix, with specified color.
        *this is a better way to print character on matrix*, with it, you do not need to write matrix frame yourself.

        :param text: max 25 characters, only allow char byte in 0~256
        :param color: color of the char
        :param fps: 1 to 30
        :param wait: if the programs wait until completion
        """
        pass

    @abstractmethod
    def set_matrix_character(self, character: str, color: str):
        """
        Sets a character on the matrix with color specified
        :param character: output character
        :param color: 6 digit hex RGB color, e.g. "ffffff", '00ff00'
        """
        pass


class SpheroBoltGPT(ABC):
    """
    the sphero bolt robot api
    """
    body: Ball
    """your ball body"""

    face: LedMatrix
    """your ball face"""

    def save_expression(
            self,
            name: str,
            desc: str,
            builder: Callable[[Ball, LedMatrix], None]
    ) -> None:
        """
        create a named expression that express your feelings and can call it by name later.
        :param name: name of the expression
        :param desc: desc of the expression
        :param builder: define the movement and the animation combined that express your feeling.
        :return:
        """
        pass

    def run(self, expression_name: str) -> None:
        """
        run a defined expression
        :param expression_name: saved expression name
        """
        pass
