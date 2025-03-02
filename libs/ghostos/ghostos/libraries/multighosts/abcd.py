from typing import List, Union, Iterable
from abc import ABC, abstractmethod
from ghostos.abcd import Operator, Ghost

__all__ = ['MultiGhosts']


class MultiGhosts(ABC):
    """
    Ghost is alias of conversational AI agent.
    Multi-Ghosts Lib is useful to organize group chat of some topics.
    1. each topic have it own chat thread. the same ghost in the different topic do not share memory.
    2. ghost can only see your message, public message, and private group messages.
    3. record important log of your topic.
    4. you may create multi topics, but make sure less than 10 at a time. clear the done topics in time.
    """

    @abstractmethod
    def save_ghosts(self, *ghosts: Ghost) -> None:
        """
        save the ghost instances
        """
        pass

    @abstractmethod
    def get_ghosts(self, *names: str) -> List[Ghost]:
        """
        get the ghost instances from saved
        :param names: names of the ghosts. if empty, get all the ghosts
        """
        pass

    @abstractmethod
    def create_topic(self, name: str, description: str, ghosts: List[Union[Ghost, str]]) -> None:
        """
        create a new topic with certain ghosts participating.
        :param name: the unique name of the topic
        :param description: describes the topic for recalling.
        :param ghosts: ghost instance or saved ghost names.
        """
        pass

    @abstractmethod
    def add_log(self, topic: str, message: str) -> None:
        """
        add log to topic in case you forget them. only you can see the logs.
        :param topic: name of the topic.
        :param message: log content
        """
        pass

    @abstractmethod
    def public_chat(self, topic: str, message: str, names: Iterable[str]) -> Operator:
        """
        let the ghosts speak one by one, share the conversation to each other.
        :param topic: the created topic name
        :param message: send to each ghost
        :param names: the speech order of ghosts, if empty, all the ghosts in the topic will speak
        :return: Operator to start this chat round
        """
        pass

    @abstractmethod
    def clear_topics(self, *topics: str) -> None:
        """
        clear the topic.
        """
        pass

#
# @abstractmethod
# def private_chat(
#         self,
#         topic: str,
#         message: str,
#         names: List[str],
# ) -> Operator:
#     """
#     let some ghosts speak one by one, privately. Only speaking ones can see this round.
#     :param topic: the created topic name
#     :param message: the question content
#     :param names: the privately speaking ghost names.
#     :return: Operator to start this round
#     """
#     pass
#
# @abstractmethod
# def parallel_chat(
#         self,
#         topic: str,
#         message: str,
#         *names: str,
# ) -> Operator:
#     """
#     wait a group of ghosts replying in parallel. Only You can see the whole responses from each.
#     :param topic: the created topic name
#     :param message: the message you send to each ghost.
#     :param names: the names of the selected ghosts, if empty, all the ghosts in the topic will receive it.
#     :return: Operator to start this chat round
#     """
#     pass
#
# @abstractmethod
# def async_chat(
#         self,
#         topic: str,
#         message: str,
#         *names: str,
# ) -> Operator:
#     """
#     just like the parallel_chat, but you will receive each ghost's reply asynchronously.
#     :return: Operator to start this chat round
#     """
