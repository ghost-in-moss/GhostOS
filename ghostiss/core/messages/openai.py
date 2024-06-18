from typing import Union, Dict

from openai.types.chat.chat_completion import ChatCompletionMessage
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from openai.types.chat.chat_completion_assistant_message_param import ChatCompletionAssistantMessageParam
from openai.types.chat.chat_completion_function_message_param import ChatCompletionFunctionMessageParam
from openai.types.chat.chat_completion_tool_message_param import ChatCompletionToolMessageParam

__all__ = [
    "ChatCompletionMessage",
    "ChatCompletionSystemMessageParam", "ChatCompletionUserMessageParam", "ChatCompletionAssistantMessageParam",
    "ChatCompletionFunctionMessageParam", "ChatCompletionToolMessageParam",
    "OPENAI_MESSAGE_TYPES",
]

OPENAI_MESSAGE_TYPES = Union[
    Dict,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionMessage,
]

