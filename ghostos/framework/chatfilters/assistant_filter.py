from typing import Optional
from ghostos.core.messages import Message, Role
from ghostos.core.llms import ChatPreparer, Chat
from ghostos.core.session import TaskPayload


class OtherAgentOrTaskPreparer(ChatPreparer):
    """
    调整 assistant name, 如果一条 assistant 消息的 name 与当前 name 相同则去掉.
    这样就会认为是自己的消息.
    """

    def __init__(self, *, assistant_name: str, task_id: str = "", with_task_name: bool = False):
        self._assistant_name = assistant_name
        self._task_id = task_id
        self._with_task_name = with_task_name

    def prepare_chat(self, chat: Chat) -> Chat:
        def filter_fn(message: Message) -> Optional[Message]:
            if message.role != Role.ASSISTANT.value:
                return message

            copy = None
            if message.name != self._assistant_name:
                copy = message.get_copy()
                copy.name = ""

            task_payload = TaskPayload.read(message)
            # 判断是否要做任务信息的改造.
            if task_payload is None or message.memory is None or task_payload.task_id == self._task_id:
                return copy if copy else message

            copy = copy if copy else message.get_copy()
            # 对齐用户所见的消息体.
            copy.memory = None
            if self._with_task_name:
                copy.name = "task." + task_payload.name
            return copy

        chat.filter_messages(filter_fn)
        return chat
