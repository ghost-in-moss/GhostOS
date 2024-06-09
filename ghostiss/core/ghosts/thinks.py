from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar, Generic, Tuple, Optional
from pydantic import BaseModel
from ghostiss.context import Context

if TYPE_CHECKING:
    from ghostiss.core.kernel.runs import Run
    from ghostiss.core.kernel.llms import Chat
    from ghostiss.core.messages import Message
    from ghostiss.core.ghosts.ghost import Ghost

R = TypeVar('R', bound=BaseModel)


class Quest(Generic[R], BaseModel):

    @abstractmethod
    def to_chat(self) -> Chat:
        pass

    @abstractmethod
    def on_result(self, msg: Message) -> R:
        pass


class Thinks(ABC):
    """
    基于大模型实现各种底层范式.
    """

    def chat(self, ctx: Context, run: Run):
        """
        一轮对话.
        """
        pass

    def choose(self):
        """
        多个选项中选择一个.
        """
        pass

    def select(self):
        """
        多个选项中挑选多个.
        """
        pass

    def choose_action(self):
        """
        在一次流式运行中, 返回一步操作.
        """
        pass

    def multi_actions(self):
        """
        在一次流式运行中, 返回多步操作.
        """
        pass

    def run_quest(self, ctx: Context, quest: Quest[R]) -> Tuple[R, Optional[Exception]]:
        pass
