import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Iterable, Callable, Set
from queue import Queue
from ghostos.contracts.logger import LoggerItf
from ghostos.core.messages import Message, ReceiverBuffer, SequencePipe


class OutputBuffer(ABC):
    @abstractmethod
    def stop_output(self, response_id: Optional[str]):
        """
        stop the current response.
        """
        pass

    @abstractmethod
    def end_output(self, response_id: str):
        pass

    @abstractmethod
    def start_output(self, response_id: str):
        """
        start a new response
        :param response_id:
        :return:
        """
        pass

    @abstractmethod
    def stop_speaking(self):
        pass

    @abstractmethod
    def is_speaking(self):
        pass

    @abstractmethod
    def add_response_chunk(self, response_id: str, chunk: Message) -> bool:
        """
        add a response chunk to certain response.
        :param response_id:
        :param chunk:
        :return:
        """
        pass

    @abstractmethod
    def add_message(self, message: Message, previous_item_id: Optional[str]) -> bool:
        """
        add complete message to the output. the already sent message will not be sent again.
        :param message:
        :param previous_item_id:
        :return:
        """
        pass

    @abstractmethod
    def get_outputted_messages(self) -> List[Message]:
        """
        get already outputted messages.
        :return:
        """
        pass

    @abstractmethod
    def get_response_id(self) -> Optional[str]:
        """
        get current response id.
        :return:
        """
        pass

    @abstractmethod
    def add_audio_output(self, response_id: str, data: Optional[bytes], filetype: str = "wav") -> bool:
        """
        send an audio message to output.
        :param response_id:
        :param data:
        :param filetype:
        :return:
        """
        pass

    @abstractmethod
    def add_error_message(self, error: Message):
        """
        add error message
        :param error:
        :return:
        """
        pass

    @abstractmethod
    def output_received(self) -> Optional[ReceiverBuffer]:
        """
        :return:
        """
        pass

    @abstractmethod
    def speaking_queue(self, response_id: str) -> Optional[Queue]:
        """
        get uncanceled response speaking queue.
        :param response_id:
        :return:
        """
        pass


class DefaultOutputBuffer(OutputBuffer):

    def __init__(
            self,
            is_close_check: Callable[[], bool],
            logger: LoggerItf,
    ):
        self.is_close_check = is_close_check
        self.logger = logger

        # response stream
        self.response_id: Optional[str] = None
        self.response_item_ids: Optional[List[str]] = None
        self.responding_item_id: Optional[str] = None
        self.response_chunks: Optional[Dict[str, List[Message]]] = None

        # speaking
        self.speak_queue: Optional[Queue] = None

        self.outputted_message_ids: List[str] = []
        self.outputted_messages: Dict[str, Message] = {}
        """the outputted messages in order"""

        self.error_messages: List[Message] = []
        """unsent error messages"""
        self._is_speaking: bool = False

        self.unsent_message_ids: List[str] = []
        self.sent_message_ids: Set[str] = set()

    def stop_output(self, response_id: Optional[str]):
        self.logger.debug("start output")
        if response_id is None or response_id == self.response_id:
            self.response_id = None
            self.response_chunks = None
            self.response_item_ids = None
            self.responding_item_id = None
            self.stop_speaking()

    def end_output(self, response_id: str):
        # self.response_id = None
        # self.response_chunks = None
        # self.response_item_ids = None
        # self.responding_item_id = None
        if response_id == self.response_id and self.speak_queue is not None:
            self.logger.debug("send none to speaking queue but not stop speaking")
            self.speak_queue.put(None, block=False)

    def start_output(self, response_id: str):
        self.stop_output(None)
        self.logger.debug("start output")
        self.response_id = response_id
        self.response_chunks = {}
        self.response_item_ids = []
        self.responding_item_id = None
        self.start_speaking()

    def start_speaking(self):
        self._is_speaking = True
        if self.speak_queue is not None:
            self.speak_queue.put(None, block=False)
        self.speak_queue = Queue()
        self.logger.debug("start output speaking")

    def stop_speaking(self):
        self.logger.debug("stop output speaking")
        self._is_speaking = False
        if self.speak_queue is not None:
            self.speak_queue.put(None, block=False)
            self.logger.debug("speaking queue send none")
        self.speak_queue = None

    def is_speaking(self):
        return self._is_speaking

    def add_message(self, message: Message, previous_item_id: Optional[str]) -> bool:
        if message is None or not message.is_complete():
            return False
        if not message.content:
            return False
        msg_id = message.msg_id
        # the message is a new item.
        if msg_id not in self.outputted_message_ids:
            self.outputted_messages[msg_id] = message
            self.outputted_message_ids.append(msg_id)
            self.unsent_message_ids.append(msg_id)
        else:
            self.outputted_messages[msg_id] = message
        # re-range messages
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
            self.response_chunks = {}
        if chunk.msg_id:
            self.responding_item_id = chunk.msg_id
        if not self.responding_item_id:
            self.responding_item_id = ""
        if self.responding_item_id not in self.response_chunks:
            self.response_chunks[self.responding_item_id] = []
            self.response_item_ids.append(self.responding_item_id)
        chunks = self.response_chunks[self.responding_item_id]
        chunks.append(chunk)
        return True

    def get_outputted_messages(self) -> List[Message]:
        messages = []
        for msg_id in self.outputted_message_ids:
            message = self.outputted_messages[msg_id]
            messages.append(message)
        return messages

    def get_response_id(self) -> Optional[str]:
        return self.response_id

    def add_audio_output(self, response_id: str, data: Optional[bytes], filetype: str = "wav") -> bool:
        if response_id != self.response_id:
            return False
        queue = self.speak_queue
        if queue is None:
            return False
        queue.put(data)
        return True

    def add_error_message(self, error: Message):
        self.error_messages.append(error)

    def speaking_queue(self, response_id: str) -> Optional[Queue]:
        return self.speak_queue

    def output_received(self) -> Optional[ReceiverBuffer]:
        chunks = self._output_chunks()
        if chunks is None:
            return None

        sent = SequencePipe().across(chunks)
        return ReceiverBuffer.new(sent)

    def _output_chunks(self) -> Optional[Iterable[Message]]:
        # first of all, the error message is priory
        if len(self.error_messages) > 0:
            error = self.error_messages.pop(0)
            if error.msg_id not in self.sent_message_ids:
                yield from [error]
                self.sent_message_ids.add(error.msg_id)
                return

        # if there are unsent complete message, send it.
        if len(self.unsent_message_ids) > 0:
            msg_id = self.unsent_message_ids.pop(0)
            if msg_id in self.outputted_messages and msg_id not in self.sent_message_ids:
                message = self.outputted_messages[msg_id]
                yield from [message]
                self.sent_message_ids.add(msg_id)
                return

                # output current responding
        if self.response_id is None:
            return None

        output_item_id = ""
        response_id = self.response_id
        if len(self.response_item_ids) > 0:
            output_item_id = self.response_item_ids.pop(0)
        if not output_item_id or output_item_id in self.sent_message_ids:
            return None

        while not self.is_close_check():
            if response_id != self.response_id or self.response_chunks is None:
                # stream canceled
                break
            if self.response_chunks is None:
                break
            if output_item_id in self.outputted_messages:
                break

            chunks = self.response_chunks[output_item_id]

            if len(chunks) > 0:
                first = chunks.pop(0)
                yield first
            else:
                time.sleep(0.1)

        if output_item_id in self.outputted_messages:
            yield self.outputted_messages[output_item_id]
            self.sent_message_ids.add(output_item_id)
