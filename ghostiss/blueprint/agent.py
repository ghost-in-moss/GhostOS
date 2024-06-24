from ghostiss.context import Context
from ghostiss.blueprint.agents.ghost import Ghost
from ghostiss.blueprint.agents.shell import Shell
from ghostiss.blueprint.messenger import Messenger


class Agent:
    """
    对各种抽象的统一封装.
    """

    def __init__(
            self,
            ctx: Context,
            ghost: Ghost,
            shell: Shell,
            messenger: Messenger,
    ):
        self.ctx = ctx
        self.ghost = ghost
        self.shell = shell
        self.messenger = messenger

    def finish(self) -> None:
        pass
