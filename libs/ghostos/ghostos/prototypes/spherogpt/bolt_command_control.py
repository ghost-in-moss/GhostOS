import time

try:
    import spherov2
except ImportError:
    exit("This script requires the spherov2 to be installed.")

from spherov2 import scanner
from spherov2.types import Color, ToyType

from abc import ABC, abstractmethod
from typing import Optional, List
from spherov2.sphero_edu import SpheroEduAPI
from pydantic import BaseModel, Field
from ghostos_common.helpers import Timeleft
from ghostos.abcd import Conversation
from ghostos.contracts.logger import LoggerItf
from ghostos.core.runtime import EventBus, EventTypes
from ghostos.core.messages import MessageType
from ghostos_moss.prompts import reflect_class_with_methods, reflect_code_prompt
from ghostos_container import BootstrapProvider, Container
from threading import Thread

__all__ = [
    'Command',
    'SpheroBolt',
    'SpheroEduAPI',
    'SpheroBoltProvider',
    'exports',
]


class Command(BaseModel):
    """
    Sphero Bolt Command that execute frame by frame in time.
    """
    name: str = Field("", description="aim of the command in simple words")
    duration: float = Field(
        default=0.0,
        description="the command running duration in seconds. "
                    "after the duration is reached, next command will be executed."
    )
    run_every: bool = Field(False, description="if True, the command run every frame")
    code: str = Field(description="the command code to execute in the sphero bolt runtime.")

    def run_frame(self, api: SpheroEduAPI, passed: float, frame: int) -> None:
        """
        run a single frame every tick
        :param api: SpheroEduAPI that control the sphero bolt
        :param passed: the passed time from command start to now
        :param frame: the frame number, frame == 0 means the command is starting

        for example, if you want roll at a special curve,
        you shall change head angle by passed time at each frame,
        """
        # import types in case you need.
        from spherov2.types import Color, ToyType
        # eval the python code defined in the command.
        # this is how the command work
        for line in self.code.splitlines():
            line = line.strip()
            if line:
                eval(line)

    @classmethod
    def once(cls, name: str, code: str, duration: float):
        """
        run only once, wait until duration is out
        """
        return cls(name=name, code=code, duration=duration, run_every=False)


class SpheroBolt(ABC):
    """
    Sphero Bolt interface
    Notice you can only run sphero by Command.
    """

    @abstractmethod
    def run(self, *commands: Command) -> None:
        """
        run command on sphero bolt. will always stop movement at beginning and end of the execution time.
        :param commands: the commands to execute in order
        """
        pass


class SpheroBoltImpl(SpheroBolt):

    def __init__(
            self,
            logger: LoggerItf,
            eventbus: EventBus,
            task_id: str,
            notify: bool,
            tick_interval: float = 0.01,
    ):
        self._logger: LoggerItf = logger
        self._executing_command: Optional[Command] = None
        self._command_stack: List[Command] = []
        self._timeleft: Optional[Timeleft] = None
        self._executing: bool = False
        self._task_id: str = task_id
        self._notify: bool = notify
        self._eventbus = eventbus
        self._destroyed = False
        self._main_thread: Optional[Thread] = None
        self._tick_interval = tick_interval
        self._ticked_frames: int = 0
        self._error = None

    def bootstrap(self):
        try:
            self._logger.info("SpheroBolt Bootstrap started")
            _bolt = scanner.find_BOLT()
            self._main_thread = Thread(target=self._main, args=(_bolt,))
            self._main_thread.start()
        except Exception as e:
            raise NotImplementedError("Could not find the Bolt device. " + str(e))

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        self._logger.info("SpheroBolt Bootstrap destroying")
        if self._main_thread is not None:
            self._main_thread.join()
        del self._logger
        del self._eventbus

    def __del__(self):
        self.destroy()

    def _clear_command(self, clear_all: bool):
        self._executing_command = None
        self._timeleft = None
        self._ticked_frames = 0
        self._executing = False
        if clear_all:
            self._command_stack = []

    def _command_succeeded(self):
        self._reset_command_at("succeeded", successful=True, clear_all=False)

    def _reset_command_at(self, action: str, successful: bool, clear_all: bool):
        if self._executing_command is None or self._timeleft is None:
            return
        name = self._executing_command.name
        passed = self._timeleft.passed()
        content = f"sphero bolt: command `{name}` {action} after running `{round(passed, 4)}` second"
        self._clear_command(clear_all)
        event_type = EventTypes.NOTIFY if successful else EventTypes.ERROR
        event = event_type.new(
            task_id=self._task_id,
            messages=[MessageType.TEXT.new_system(content=content)],
            callback=True,
        )
        self._eventbus.send_event(event, self._notify)

    def _main(self, bolt) -> None:
        while not self._destroyed:
            self._logger.info("SpheroBolt toy connected")
            try:
                self._run_toy(bolt)
            except Exception as e:
                self._logger.error(str(e))
                self._logger.info("SpheroBolt toy reconnecting")
        self.destroy()

    def _run_toy(self, toy) -> None:
        with SpheroEduAPI(toy) as api:
            while not self._destroyed:
                try:
                    if self._executing_command and self._timeleft:
                        api.set_front_led(Color(0, 100, 0))
                        has_duration = self._executing_command.duration > 0
                        must_run = self._ticked_frames == 0
                        run_every = self._executing_command.run_every
                        if must_run or (self._timeleft.left() > 0 and run_every):
                            self._executing_command.run_frame(
                                api,
                                self._timeleft.passed(),
                                self._ticked_frames,
                            )
                            self._ticked_frames += 1
                            if has_duration:
                                time.sleep(self._tick_interval)
                            continue
                        else:
                            self._command_succeeded()
                            api.set_front_led(Color(0, 0, 0))
                            continue
                    elif len(self._command_stack) > 0:
                        current: Command = self._command_stack.pop(0)
                        self._executing = True
                        self._executing_command = current
                        self._timeleft = Timeleft(current.duration)
                        self._ticked_frames = 0
                    else:
                        time.sleep(0.5)
                except Exception as e:
                    self._logger.exception(e)
                    self._reset_command_at(
                        f"stopped because of error {e}",
                        successful=False,
                        clear_all=True,
                    )
            self._logger.info("SpheroBolt start to stop")
        self._logger.info("SpheroBolt stopped")

    def run(self, *commands: Command) -> None:
        if self._error:
            raise RuntimeError(self._error)
        if self._executing:
            self._reset_command_at("stop during new command", successful=True, clear_all=True)
        commands = list(commands)
        if len(commands) == 0:
            return
        self._command_stack = commands


class SpheroBoltProvider(BootstrapProvider):
    """
    Sphero Bolt Provider interface
    """

    def singleton(self) -> bool:
        return True

    def contract(self):
        return SpheroBolt

    def factory(self, con: Container) -> Optional[SpheroBolt]:
        conversation = con.force_fetch(Conversation)
        eventbus = con.force_fetch(EventBus)
        logger = con.force_fetch(LoggerItf)
        task = conversation.get_task()
        return SpheroBoltImpl(
            logger,
            eventbus,
            task_id=task.task_id,
            notify=task.shall_notify(),
            tick_interval=0.01,
        )

    @staticmethod
    def bootstrap(container: Container) -> None:
        sphero_bolt = container.force_fetch(SpheroBolt)
        if isinstance(sphero_bolt, SpheroBoltImpl):
            container.add_shutdown(sphero_bolt.destroy)
            sphero_bolt.bootstrap()


exports = {
    Command.__name__: reflect_code_prompt(Command),
    SpheroBolt.__name__: reflect_code_prompt(SpheroBolt),
    SpheroEduAPI.__name__: reflect_class_with_methods(SpheroEduAPI),
}

if __name__ == "__exports__":
    from ghostos_common.helpers import yaml_pretty_dump

    print(yaml_pretty_dump(exports))

if __name__ == "__main__":
    from ghostos.framework.eventbuses import MemEventBusImpl
    from ghostos.contracts.logger import get_console_logger

    _logger = get_console_logger()
    _eventbus = MemEventBusImpl()
    sb = SpheroBoltImpl(_logger, _eventbus, "task_id", False)
    sb.bootstrap()

    # class TestCommand(Command):
    #     code: str = ""
    #
    #     def run_frame(self, api: SpheroEduAPI, passed: float, frame: int) -> None:
    #         api.roll(0, 100, 1)
    #         api.roll(90, 100, 1)
    #         api.roll(180, 100, 1)
    #         api.roll(270, 100, 1)
    #         api.roll(0, 100, 1)
    c = Command(
        name="roll in a circle",
        code="""
api.set_speed(100)
api.roll(0, 100, 1)
api.roll(90, 100, 1)
api.roll(180, 100, 1)
api.roll(270, 100, 1)
api.roll(360, 100, 1)
api.set_speed(0)
""",
        duration=5
    )

    sb.run(c)
