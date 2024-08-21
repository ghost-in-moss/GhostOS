from typing import Optional, List, Tuple, Any

from ghostiss.core.quests.itf import Step, QuestContext, QuestDriver
from ghostiss.core.session import MsgThread, DefaultEventType
from ghostiss.core.messages import Message

__all__ = ['ObserveStep', 'FinishStep']


class ObserveStep(Step):
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
    ) -> Tuple[MsgThread, Optional["Step"]]:
        thread = thread.update_history()
        thread.new_round(DefaultEventType.THINK.new(
            task_id=thread.id,
            from_task_id=thread.id,
            messages=self.messages,
        ))
        return driver.run(context.container(), context.messenger(), thread)


class FinishStep(Step):
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
    ) -> Tuple[MsgThread, Optional["Step"]]:
        context.set_result(self.value)
        return thread, None
