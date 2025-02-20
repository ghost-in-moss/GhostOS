from ghostos.prototypes.spherogpt.bolt.runtime import SpheroBoltRuntime
from ghostos.prototypes.spherogpt.bolt.runtime_impl import SpheroBoltRuntimeImpl
from ghostos.prototypes.spherogpt.bolt.bolt_shell import Ball, RollFunc
from ghostos.prototypes.spherogpt.bolt.ball_impl import SpheroBoltBallAPIProvider
from ghostos.framework.eventbuses import MemEventBusImpl, EventBus
from ghostos.framework.workspaces import BasicWorkspace
from ghostos.framework.storage import MemStorage
from ghostos.contracts.logger import get_console_logger
from ghostos.contracts.workspace import Workspace
from ghostos_container import Container

if __name__ == "__main__":
    eventbus = MemEventBusImpl()
    logger = get_console_logger()
    _runtime = SpheroBoltRuntimeImpl(task_id="task_id", eventbus=eventbus, logger=logger)
    container = Container()
    storage = MemStorage()
    _workspace = BasicWorkspace(storage)
    container.set(EventBus, eventbus)
    container.set(SpheroBoltRuntime, _runtime)
    container.set(Workspace, _workspace)
    container.register(SpheroBoltBallAPIProvider())
    container.bootstrap()
    _runtime.bootstrap()

    ball = container.get(Ball)

    # test command

    move = ball.new_move()
    curve = RollFunc(
        heading=0,
        speed=90,
        duration=6,
        code="""
    self.speed = 90
    self.heading = int((passed % 6) * 60)  # Change heading to create a circular path
    """
    )
    move.roll_by_func(curve)
    ball.run(move)
