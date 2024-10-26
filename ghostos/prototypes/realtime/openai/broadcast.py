from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from copy import deepcopy
from ghostos.prototypes.realtime.abcd import ChanIn
from ghostos.contracts.logger import LoggerItf, get_logger

__all__ = ['Broadcaster', 'SimpleBroadcaster']


class Broadcaster(ABC):
    """
    broadcast event to all channels
    """

    @abstractmethod
    def subscribe(
            self,
            subscriber: str,
            chan: ChanIn,
            topics: List[str],
    ) -> None:
        pass

    @abstractmethod
    def publish(self, topic: str, data: dict):
        pass

    @abstractmethod
    def close(self):
        pass


class SimpleBroadcaster(Broadcaster):

    def __init__(self, logger: Optional[LoggerItf] = None):
        self.subscriber_channels: Dict[str, ChanIn] = {}
        self.topic_to_subscribers: Dict[str, List[str]] = {}
        self._closed = False
        self._start_join = False
        self._logger = logger if logger else get_logger()

    def subscribe(
            self,
            subscriber: str,
            chan: ChanIn,
            topics: List[str],
    ) -> None:
        if self._closed:
            raise RuntimeError("Broadcaster already closed")
        if subscriber in self.subscriber_channels:
            raise ValueError(f"Subscriber {subscriber} already subscribed")
        self.subscriber_channels[subscriber] = chan
        for topic in topics:
            if topic not in self.topic_to_subscribers:
                self.topic_to_subscribers[topic] = []
            subscribers = self.topic_to_subscribers[topic]
            subscribers.append(subscriber)
            self.topic_to_subscribers[topic] = subscribers
        return None

    def publish(self, topic: str, data: dict):
        if self._closed:
            raise RuntimeError("Broadcaster already closed")
        if topic not in self.topic_to_subscribers:
            return
        subscribers = self.topic_to_subscribers[topic]
        if not subscribers:
            return
        for subscriber in subscribers:
            if self._closed:
                break
            chan = self.subscriber_channels[subscriber]
            copied = deepcopy(data)
            try:
                chan.put(copied, block=False, timeout=0.5)
            except TimeoutError as e:
                raise RuntimeError(f"Failed to publish because subscriber {subscriber} chan timed out: {e}")
            except Exception as e:
                self._logger.error(
                    "put topic %s event to subscriber %s failed",
                    topic, subscriber,
                    exc_info=e,
                )
                continue

    def close(self):
        if self._closed:
            return
        self._logger.info("%s is closing", self.__class__.__name__)
        self._closed = True
        for chan in self.subscriber_channels.values():
            chan.put(None)
            chan.task_done()
        self.topic_to_subscribers = {}
        self.subscriber_channels = {}
