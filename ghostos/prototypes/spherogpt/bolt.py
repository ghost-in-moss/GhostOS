import time

try:
    import spherov2
except ImportError:
    exit("This script requires the spherov2 to be installed.")

from spherov2 import scanner
from spherov2.toy import bolt

from abc import ABC, abstractmethod
from typing import Optional
from spherov2.sphero_edu import SpheroEduAPI
from pydantic import BaseModel, Field
from ghostos.helpers import Timeleft
from ghostos.abcd import Conversation
from ghostos.core.runtime import EventBus, EventTypes
from ghostos.core.messages import MessageType
from ghostos.core.moss.prompts import reflect_class_with_methods, get_prompt
from ghostos.container import BootstrapProvider, Container
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
    name: str = Field(description="aim of the command in simple words")
    duration: float = Field(
        description="the command running duration in seconds. "
                    "when the duration tick out, the bolt stop."
                    "if duration is 0, execute once.")
    code: str = Field(description="the command code")
    execution_log: str = Field(default="", description="the command execution log, only used at the command runtime")

    def run_frame(self, api: SpheroEduAPI, passed: float, frame: int) -> None:
        """
        run a single frame every tick
        :param api: SpheroEduAPI that controll the sphero bolt
        :param passed: the passed time from command start to now
        :param frame: the frame number, frame == 0 means the command is starting
        :return: None
        """
        # eval the python code defined in the command.
        eval(self.code)


class SpheroBolt(ABC):
    """
    Sphero Bolt interface
    """

    @abstractmethod
    def run(self, *commands: Command) -> None:
        """
        run command on sphero bolt. will always stop movement at beginning and end of the execution time.
        :param commands: the commands, could be a pipeline
        :param tick: the interval time between frames in secondes
        :return: None, but will send message after the running.
        """
        pass


class SpheroBoltImpl(SpheroBolt):

    def __init__(
            self,
            eventbus: EventBus,
            task_id: str,
            notify: bool,
            tick_interval: float = 0.01,
    ):
        self._executing_command: Optional[Command] = None
        self._command_stack: List[Command] = []
        self._timeleft: Optional[Timeleft] = None
        self._executing: bool = False
        self._task_id: str = task_id
        self._notify: bool = notify
        self._eventbus = eventbus
        self._destroyed = False
        self._main_thread = Thread(target=self._main)
        self._tick_interval = tick_interval
        self._ticked_frames: int = 0
        self._bolt: Optional[bolt] = None

    def bootstrap(self):
        try:
            self._bolt = scanner.find_BOLT()
            if self._bolt is not None:
                self._main_thread.start()
        except Exception as e:
            raise NotImplementedError("Could not find the Bolt device. " + str(e))

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        if self._bolt is not None:
            self._main_thread.join()
        del self._bolt
        del self._eventbus

    def __del__(self):
        self.destroy()

    def _clear_command(self):
        self._executing_command = None
        self._timeleft = None
        self._ticked_frames = 0
        self._executing = False

    def _command_succeeded(self):
        self._reset_command_at("succeeded")

    def _reset_command_at(self, action: str):
        if self._executing_command is None or self._timeleft is None:
            return
        name = self._executing_command.name
        passed = self._timeleft.passed()
        content = f"command `{name}` {action} after running `{round(passed, 4)}` second"
        self._clear_command()
        event = EventTypes.NOTIFY.new(
            task_id=self._task_id,
            messages=[MessageType.TEXT.new_system(content=content)]
        )
        self._eventbus.send_event(event, self._notify)

    def _main(self) -> None:
        with SpheroEduAPI(self._bolt) as api:
            while not self._destroyed:
                if self._executing_command and self._timeleft:
                    if self._executing_command.duration <= 0:
                        self._executing_command.run_frame(api, 0, 0)
                        self._command_succeeded()
                        continue
                    elif self._timeleft.alive():
                        self._executing_command.run_frame(api, self._timeleft.passed(), self._ticked_frames)
                        self._ticked_frames += 1
                        time.sleep(self._tick_interval)
                        continue
                    else:
                        self._command_succeeded()
                elif len(self._command_stack) > 0:
                    current: Command = self._command_stack.pop(0)
                    self._executing = True
                    self._executing_command = current
                    self._timeleft = Timeleft(current.duration)
                    self._ticked_frames = 0
                else:
                    time.sleep(0.5)
            api.stop_roll()

    def run(self, *commands: Command) -> None:
        if self._bolt is None:
            raise RuntimeError(f"Sphero Bolt is not initialized.")
        if self._executing:
            self._reset_command_at("stop during new command")
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
        task = conversation.task()
        return SpheroBoltImpl(
            eventbus,
            task_id=task.task_id,
            notify=task.shall_notifiy(),
            tick_interval=0.01,
        )

    def bootstrap(self, container: Container) -> None:
        sphero_bolt = container.force_fetch(SpheroBolt)
        if isinstance(sphero_bolt, SpheroBoltImpl):
            sphero_bolt.bootstrap()
            container.add_shutdown(sphero_bolt.destroy)


exports = {
    Command.__name__: get_prompt(Command),
    SpheroBolt.__name__: get_prompt(SpheroBolt),
    SpheroEduAPI.__name__: reflect_class_with_methods(SpheroEduAPI),
}

if __name__ == "__main__":
    from ghostos.helpers import yaml_pretty_dump

    print(yaml_pretty_dump(exports))
