from typing import Optional, List, Tuple, Any

from ghostiss.core.quests.itf import QuestOperator, QuestContext, QuestDriver
from ghostiss.core.session import MsgThread, DefaultEventType
from ghostiss.core.messages import Message

__all__ = ['ObserveOperator', 'FinishOperator']


class ObserveOperator(QuestOperator):
    """
    继续观察.
    """

    def __init__(self, messages: List[Message]):
        self.messages = messages

    def next(
            self,
            context: "QuestContext",
            driver: "QuestDriver",
            thread: MsgThread,
    ) -> Tuple[MsgThread, Optional["QuestOperator"]]:
        thread = thread.update_history()
        thread.new_turn(DefaultEventType.THINK.new(
            task_id=thread.id,
            from_task_id=thread.id,
            messages=self.messages,
        ))
        return driver.run(context.container(), context.messenger(), thread)


class FinishOperator(QuestOperator):
    """
    结束运行, 并且赋值.
    """

    def __init__(self, value: Any):
        self.value = value

    def next(
            self,
            context: "QuestContext",
            driver: "QuestDriver",
            thread: MsgThread,
    ) -> Tuple[MsgThread, Optional["QuestOperator"]]:
        context.set_result(self.value)
        return thread, None
