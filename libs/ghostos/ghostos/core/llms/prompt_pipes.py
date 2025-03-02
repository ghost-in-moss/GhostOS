from typing import Optional
from ghostos.core.messages import Message, Role
from ghostos.core.llms import PromptPipe, Prompt

__all__ = ['AssistantNamePipe']


class AssistantNamePipe(PromptPipe):
    """
    调整 assistant name, 如果一条 assistant 消息的 name 与当前 name 相同则去掉.
    这样就会认为是自己的消息.
    """

    def __init__(self, assistant_name: str):
        self._assistant_name = assistant_name

    def update_prompt(self, prompt: Prompt) -> Prompt:
        def filter_fn(message: Message) -> Optional[Message]:
            if message.role != Role.ASSISTANT.value:
                return message

            copy = message
            if message.name == self._assistant_name:
                copy = message.get_copy()
                copy.name = ""
            return copy

        prompt.filter_messages(filter_fn)
        return prompt
