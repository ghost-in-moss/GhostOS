from typing import Optional, Callable, Type
import time

from ghostos.contracts.logger import LoggerItf
from ghostos.core.messages import MessageType
from ghostos.core.runtime import EventBus, Event, EventTypes as GhostOSEventTypes
from ghostos.container import Container, BootstrapProvider, INSTANCE
from ghostos.abcd import Conversation
from ghostos.helpers import Timeleft
from threading import Thread, Event
from collections import deque

from .bolt_shell import Animation
from .sphero_edu_api_patch import SpheroEduAPI, Color, SpheroEventType, scanner
from .runtime import SpheroBoltRuntime, BoltLedMatrixCommand, BoltBallMovement
from .led_matrix_impl import PlayAnimation

__all__ = ['SpheroBoltRuntimeImpl', 'ConvoLevelSpheroBoltRuntimeProvider']


class SpheroBoltRuntimeImpl(SpheroBoltRuntime):

    def __init__(
            self,
            *,
            task_id: str,
            eventbus: EventBus,
            logger: LoggerItf,
            shall_notify: bool = False,
    ):
        self._task_id = task_id
        self._shall_notify = shall_notify
        self._eventbus = eventbus
        self._logger = logger
        self._stopped = Event()
        self._closed = False
        self._bootstrapped = False
        self._error: Optional[str] = None
        self._main_thread = Thread(target=self._main_thread)
        self._move_queue = deque()
        self._animation_queue = deque()
        self._current_animation: Optional[BoltLedMatrixCommand] = None
        self._current_animation_timeleft: Optional[Timeleft] = None
        self._clear_matrix_timeleft: Optional[Timeleft] = None
        self._current_movement: Optional[BoltBallMovement] = None
        self._current_movement_timeleft: Optional[Timeleft] = None
        self._charging_callback: str = "feeling at charging"
        self._breathing: bool = False
        self._moving: bool = False
        self._off_charging_callback: str = "feeling stop charging"

    def _reset_all_state(self):
        self._current_animation = None
        self._current_animation_timeleft = None
        self._current_movement = None
        self._current_movement_timeleft = None
        self._animation_queue.clear()
        self._move_queue.clear()

    def bootstrap(self):
        if self._bootstrapped:
            self._logger.error(f"SpheroBolt Runtime already bootstrapped")
            return
        self._bootstrapped = True
        self._main_thread.start()

    def _main_thread(self):
        connected_error = 0
        while not self._stopped.is_set():
            try:
                self._logger.info("SpheroBolt Bootstrap started")
                _bolt = scanner.find_BOLT()
                self._logger.info("SpheroBolt Bootstrap connected")
                connected_error = 0
                # run the loop until errors.
                try:
                    self._run_bolt_loop(_bolt)
                except Exception as exc:
                    self._logger.exception(exc)
                    self._send_event(GhostOSEventTypes.ERROR, "error occur during runtime: %s" % str(exc))
                    self._reset_all_state()
                    continue

            except Exception as e:
                self._logger.exception(e)
                self._logger.info("SpheroBolt Bootstrap failed")
                connected_error += 1
                if connected_error > 3:
                    self._stopped.set()
                    self._error = 'failed to connected SpheroBolt'
                    self._send_event(GhostOSEventTypes.ERROR, "sphero bolt failed to connected")
                    raise RuntimeError(self._error)

    def _strobe(self, api: SpheroEduAPI, passed: float):
        if self._moving:
            return
        if int(passed) % 6 < 3:
            if not self._breathing:
                api.set_front_led(Color(0, 25, 0))
                api.set_back_led(Color(0, 25, 0))
                self._breathing = True
        elif self._breathing:
            api.set_front_led(Color(0, 0, 0))
            api.set_back_led(Color(0, 0, 0))
            self._breathing = False

    def _set_current_animation(self, animation: BoltLedMatrixCommand, api: SpheroEduAPI):
        animation.start(api)
        self._current_animation = animation
        self._current_animation_timeleft = Timeleft(0)

    def _check_end_of_animation(self, api: SpheroEduAPI):
        if self._current_animation is None or self._current_animation_timeleft is None:
            return
        if self._current_animation.end(api, self._current_animation_timeleft.passed()):
            self._current_animation = None
            self._current_animation_timeleft = None

    def _run_bolt_loop(self, _bolt):
        start_at = Timeleft(0)
        with SpheroEduAPI(_bolt) as api:
            self._init_sphero_edu_api(api)
            while not self._stopped.is_set():
                if len(self._animation_queue) > 0:
                    self._current_animation = None
                    self._current_animation_timeleft = None
                    animation_command: Optional[BoltLedMatrixCommand] = self._animation_queue.popleft()
                    # animation command execute immediately
                    self._set_current_animation(animation_command, api)

                # trigger end of animation.
                self._check_end_of_animation(api)

                if self._current_movement is None:
                    movement = self._get_new_movement()
                    if movement is not None:
                        self._set_current_movement(movement, api)
                    else:
                        self._strobe(api, start_at.passed())
                        time.sleep(0.5)
                    continue
                else:
                    passed = self._current_movement_timeleft.passed()
                    stopped = self._current_movement.run_frame(api, passed)
                    if stopped:
                        self._clear_current_movement(api)

    def _init_sphero_edu_api(self, api):
        events = [
            SpheroEventType.on_landing,
            SpheroEventType.on_freefall,
            SpheroEventType.on_collision,
        ]
        for event in events:
            listener = self._get_listener(event, api)
            api.register_event(event, listener)

    def _get_listener(self, event_type: SpheroEventType, api: SpheroEduAPI) -> Callable[[], None]:
        def callback():
            if self._current_movement is not None:
                self._clear_current_movement(api, event_type.name)
                move = self._current_movement.on_event(event_type.name)
                if move is not None:
                    self._set_current_movement(move, api)
                else:
                    self._default_on_event(event_type, api)

        return callback

    def _default_on_event(self, event_type: SpheroEventType, api: SpheroEduAPI):
        api.stop_roll()
        api.clear_matrix()
        if event_type == SpheroEventType.on_charging:
            self._send_event(GhostOSEventTypes.NOTIFY, self._charging_callback)
        elif event_type == SpheroEventType.on_not_charging:
            self._send_event(GhostOSEventTypes.NOTIFY, self._off_charging_callback)
        return

    def _set_current_movement(self, movement: BoltBallMovement, api: SpheroEduAPI):
        if movement is None:
            return

        self._current_movement = movement
        self._current_movement_timeleft = Timeleft(0)
        self._moving = True
        # always clear matrix at first.
        if movement.animation is not None:
            api.clear_matrix()
            pa = PlayAnimation(animation=movement.animation)
            self.add_matrix_command(pa)

        api.set_front_led(Color(0, 200, 0))
        self._logger.debug("start new movement %r", movement)
        movement.start(api)

    def _clear_current_movement(self, api: SpheroEduAPI, interrupt: Optional[str] = None):
        if self._current_movement is not None and self._current_movement_timeleft is not None:
            api.stop_roll()
            api.set_front_led(Color(0, 0, 0))
            self._moving = False
            if self._current_movement.animation is not None:
                api.clear_matrix()
            if not interrupt:
                log = self._current_movement.succeed_log(self._current_movement_timeleft.passed())
                if log:
                    self._send_event(GhostOSEventTypes.NOTIFY, log)
            else:
                log = self._current_movement.interrupt_log(interrupt, self._current_movement_timeleft.passed())
                if log:
                    self._send_event(GhostOSEventTypes.NOTIFY, log)

        self._current_movement = None
        self._current_movement_timeleft = None

    def _get_new_movement(self) -> Optional[BoltBallMovement]:
        if len(self._move_queue) == 0:
            return None
        movement: BoltBallMovement = self._move_queue.popleft()
        return movement

    def _send_event(self, event_type: GhostOSEventTypes, content: str):
        event = event_type.new(
            task_id=self._task_id,
            messages=[MessageType.TEXT.new_system(content=content)],
            callback=True,
        )
        self._eventbus.send_event(event, self._shall_notify)

    def add_movement(self, move: BoltBallMovement):
        if move.stop_at_first:
            self._move_queue.clear()
            self._move_queue.append(move)
        else:
            self._move_queue.append(move)

    def add_animation(self, animation: Animation) -> None:
        pa = PlayAnimation(animation=animation)
        self.add_matrix_command(pa)

    def add_matrix_command(self, command: BoltLedMatrixCommand):
        self._animation_queue.append(command)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._stopped.set()

    def get_task_id(self) -> str:
        return self._task_id

    def set_charging_callback(self, event: str):
        self._charging_callback = event

    def set_off_charging_callback(self, event: str):
        self._off_charging_callback = event


class ConvoLevelSpheroBoltRuntimeProvider(BootstrapProvider):

    def contract(self) -> Type[INSTANCE]:
        return SpheroBoltRuntime

    def bootstrap(self, container: Container) -> None:
        runtime = container.force_fetch(SpheroBoltRuntime)
        runtime.bootstrap()
        container.add_shutdown(runtime.close)

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[SpheroBoltRuntime]:
        logger = con.force_fetch(LoggerItf)
        logger.error("runtime bootstrap at container %s", con.bloodline)
        conversation = con.force_fetch(Conversation)
        task = conversation.get_task()
        eventbus = con.force_fetch(EventBus)
        return SpheroBoltRuntimeImpl(
            task_id=task.task_id,
            eventbus=eventbus,
            logger=logger,
            shall_notify=task.shall_notify(),
        )
