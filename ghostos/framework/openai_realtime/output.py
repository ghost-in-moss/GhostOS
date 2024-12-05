import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Iterable, Callable
from queue import Queue
from ghostos.contracts.logger import LoggerItf
from ghostos.core.messages import Message, ReceiverBuffer, SequencePipe


class OutputBuffer(ABC):
    @abstractmethod
    def stop_response(self):
        pass

    @abstractmethod
    def start_response(self, response_id: str):
        pass

    @abstractmethod
    def add_response_chunk(self, response_id: str, chunk: Message) -> bool:
        pass

    @abstractmethod
    def add_message(self, message: Message, previous_item_id: Optional[str]) -> bool:
        pass

    @abstractmethod
    def get_outputted_messages(self) -> List[Message]:
        pass

    @abstractmethod
    def get_response_id(self) -> Optional[str]:
        pass

    @abstractmethod
    def add_audio_output(self, response_id: str, data: bytes, filetype: str = "wav") -> bool:
        pass

    @abstractmethod
    def add_error_message(self, error: Message):
        pass

    @abstractmethod
    def output_item(self) -> Optional[ReceiverBuffer]:
        pass

    @abstractmethod
    def speaking_queue(self, response_id: str) -> Optional[Queue]:
        pass


class DefaultOutputBuffer(OutputBuffer):

    def __init__(
            self,
            close_check: Callable[[], bool],
            logger: LoggerItf,
    ):
        self.logger = logger
        # status.
        self.response_id: Optional[str] = None
        self.response_chunks: Optional[List[Message]] = None
        self.speak_queue: Optional[Queue] = None
        self.close_check = close_check

        self.outputted_message_ids: List[str] = []
        self.outputted_messages: Dict[str, Message] = {}
        self.error_messages: List[Message] = []
        self.unsent_message_ids: List[str] = []

    def stop_response(self):
        self.response_id = None
        self.response_chunks = None
        if self.speak_queue is not None:
            self.speak_queue.put(None)
        self.speak_queue = None

    def start_response(self, response_id: str):
        self.response_id = response_id
        self.response_chunks = []
        self.speak_queue = Queue()

    def add_message(self, message: Message, previous_item_id: Optional[str]) -> bool:
        if message is None or not message.is_complete():
            return False
        msg_id = message.msg_id
        if msg_id not in self.outputted_message_ids:
            self.outputted_message_ids.append(msg_id)
            self.unsent_message_ids.append(msg_id)
        self.outputted_messages[msg_id] = message
        if previous_item_id is not None:
            outputted_message_ids = []
            current_message_id = msg_id
            inserted = False
            for msg_id in self.outputted_message_ids:
                if msg_id == current_message_id:
                    continue
                outputted_message_ids.append(msg_id)
                if msg_id == previous_item_id:
                    outputted_message_ids.append(current_message_id)
                    inserted = True
            if not inserted:
                outputted_message_ids.append(current_message_id)
            self.outputted_message_ids = outputted_message_ids

        return True

    def add_response_chunk(self, response_id: str, chunk: Message) -> bool:
        if chunk is None:
            return False
        if response_id != self.response_id:
            return False
        if self.response_chunks is None:
            self.response_chunks = [chunk]
        else:
            self.response_chunks.append(chunk)
        return True

    def get_outputted_messages(self) -> List[Message]:
        messages = []
        for msg_id in self.outputted_message_ids:
            message = self.outputted_messages[msg_id]
            messages.append(message)
        return messages

    def get_response_id(self) -> Optional[str]:
        return self.response_id

    def add_audio_output(self, response_id: str, data: bytes, filetype: str = "wav") -> bool:
        if response_id != self.response_id:
            return False
        queue = self.speak_queue
        if queue is None:
            return False
        queue.put(data)

    def add_error_message(self, error: Message):
        self.error_messages.append(error)

    def speaking_queue(self, response_id: str) -> Optional[Queue]:
        return self.speak_queue

    def output_item(self) -> Optional[ReceiverBuffer]:
        chunks = self._output_chunks()
        if chunks is None:
            return None

        sent = SequencePipe().across(chunks)
        return ReceiverBuffer.new(sent)

    def _output_chunks(self) -> Optional[Iterable[Message]]:
        if len(self.error_messages) > 0:
            error = self.error_messages.pop(0)
            return [error]

        if len(self.unsent_message_ids) > 0:
            msg_id = self.unsent_message_ids.pop(0)
            if msg_id not in self.outputted_message_ids:
                message = self.outputted_messages[msg_id]
                return [message]

        if self.response_id is None:
            return None

        chunk_idx = 0
        output_item_id = ""
        response_id = self.response_id
        while not self.close_check():
            if response_id != self.response_id or self.response_chunks is None:
                break

            if output_item_id in self.outputted_messages:
                continue

            if len(self.response_chunks) > chunk_idx:
                item = self.response_chunks[chunk_idx]
                output_item_id = item.msg_id
                if item.is_complete():
                    if output_item_id not in self.outputted_messages:
                        self.outputted_messages[output_item_id] = item
                    yield item
                    break
                chunk_idx += 1
                yield item
            else:
                time.sleep(0.1)
