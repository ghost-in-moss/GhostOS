from typing import Optional, ClassVar, Self
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
from .event_data_objects import SessionObject, MessageItem

__all__ = [
    'ClientEventType',
    'ClientEvent',

    # 9 client events

    'SessionUpdate',
    'ConversationItemCreate',
    'ConversationItemDelete',
    'ConversationItemTruncate',

    'InputAudioBufferClear',
    'InputAudioBufferAppend',
    'InputAudioBufferCommit',

    'ResponseCreate',
    'ResponseCancel'
]


class ClientEventType(str, Enum):
    session_update = "session.updated"
    input_audio_buffer_append = "input_audio_buffer.append"
    input_audio_buffer_commit = "input_audio_buffer.commit"
    """
    1. This event will produce an error if the input audio buffer is empty. 
    2. When in Server VAD mode, the client does not need to send this event.
    3. Committing the input audio buffer will trigger input audio transcription.
       (if enabled in session configuration)
    4. it will not create a response from the model. 
    5. The server will respond with an input_audio_buffer.committed event.
    """

    input_audio_buffer_clear = "input_audio_buffer.clear"

    conversation_item_create = "conversation.item.create"
    conversation_item_truncate = "conversation.item.truncate"
    conversation_item_delete = "conversation.item.delete"

    response_create = "response.create"
    """
    1. When in Server VAD mode, the server will create Responses automatically. 
    2. A Response will include at least one Item, and may have two, in which case the second will be a function call. 
    3. These Items will be appended to the conversation history. 
    4. The server will respond with:
       1) a response.created event, 
       2) events for Items and content created, 
       3) and finally a response.done event to indicate the Response is complete. 
    5. The response.create event includes inference configuration like instructions, and temperature. 
    6. These fields will override the Session's configuration for **this Response only**.
    """

    response_cancel = "response.cancel"
    """
    1. The server will respond with a response.cancelled event 
    2. or an error if there is no response to cancel.
    """


# ---- client side events ---- #


class ClientEvent(BaseModel, ABC):
    type: ClassVar[str]
    event_id: Optional[str] = Field(
        default=None,
        description="Optional client-generated ID used to identify this event.",
    )

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)


class SessionUpdate(ClientEvent):
    type: ClassVar[str] = ClientEventType.session_update.value
    session: SessionObject


class InputAudioBufferAppend(ClientEvent):
    type: ClassVar[str] = ClientEventType.input_audio_buffer_append.value
    audio: str = Field()

    @classmethod
    def new(cls, audio: bytes) -> Self:
        raise NotImplementedError("todo")


class InputAudioBufferCommit(ClientEvent):
    """
    Send this event to commit the user input audio buffer,
    which will create a new user message item in the conversation.
    This event will produce an error if the input audio buffer is empty.
    When in Server VAD mode, the client does not need to send this event,
    the server will commit the audio buffer automatically.
    Committing the input audio buffer will trigger input audio transcription (if enabled in session configuration),
    but it will not create a response from the model.
    The server will respond with an input_audio_buffer.committed event.
    """
    type: ClassVar[str] = ClientEventType.input_audio_buffer_commit.value


class InputAudioBufferClear(ClientEvent):
    """
    Send this event to clear the audio bytes in the buffer.
    The server will respond with an input_audio_buffer.cleared event.
    """
    type: ClassVar[str] = ClientEventType.input_audio_buffer_clear.value


class ConversationItemCreate(ClientEvent):
    type: ClassVar[str] = ClientEventType.conversation_item_create.value
    previous_item_id: str = Field("")
    item: MessageItem = Field()


class ConversationItemTruncate(ClientEvent):
    type: ClassVar[str] = ClientEventType.conversation_item_truncate.value
    item_id: str = Field()
    content_index: int = Field(0)
    audio_end_ms: int = Field()


class ConversationItemDelete(ClientEvent):
    type: ClassVar[str] = ClientEventType.conversation_item_delete.value
    item_id: str = Field()


class ResponseCreate(ClientEvent):
    type: ClassVar[str] = ClientEventType.response_create.value
    response: Optional[SessionObject] = Field(None)


class ResponseCancel(ClientEvent):
    type: ClassVar[str] = ClientEventType.response_cancel.value