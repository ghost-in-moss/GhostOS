from typing import List, Union, Iterable
from abc import ABC, abstractmethod

from ghostos.abcd import Operator, Ghost
from ghostos.libraries.multighosts.abcd import MultiGhosts
from ghostos.libraries.multighosts.data import MultiGhostData, Topic
from ghostos.libraries.multighosts.operators import PublicChatOperator
from ghostos_common.prompter import POM


class BaseMultiGhosts(MultiGhosts, POM, ABC):

    def __init__(self, *, hostname: str, data: MultiGhostData) -> None:
        self._hostname = hostname
        self._data = data

    @abstractmethod
    def _save_data(self):
        pass

    def save_ghosts(self, *ghosts: Ghost) -> None:
        self._data.ghosts.add_ghosts(*ghosts)

    def get_ghosts(self, *names: str) -> List[Ghost]:
        ghosts = []
        names = list(names)
        if len(names) == 0:
            names = list(self._data.ghosts.identities.keys())
        for name in names:
            ghost = self._data.ghosts.get_ghost(name)
            ghosts.append(ghost)
        return ghosts

    def get_single_ghost(self, name: str) -> Ghost:
        ghost = self._data.ghosts.get_ghost(name)
        return ghost

    def create_topic(self, name: str, description: str, ghosts: List[Union[Ghost, str]]) -> None:
        ghosts_instances = []
        for ghost in ghosts:
            if isinstance(ghost, Ghost):
                ghosts_instances.append(ghost)
            elif isinstance(ghost, str):
                ghost_name = ghost
                instance = self.get_single_ghost(ghost_name)
                ghosts_instances.append(instance)
            else:
                raise AttributeError(f"Invalid ghost type: {type(ghost)}")

        topic = Topic(name=name, description=description)
        topic.add_ghosts(*ghosts_instances)
        self._data.topics[name] = topic
        self._save_data()

    def add_log(self, topic: str, message: str) -> None:
        t = self._data.topics.get(topic, None)
        if t is None:
            raise AttributeError(f"Topic {topic} does not exist")
        t.logs.append(message)

    def public_chat(self, topic: str, message: str, names: Iterable[str]) -> Operator:
        topic_data = self._data.topics.get(topic)
        if topic_data is None:
            raise AttributeError(f"Not found topic: {topic}")
        names = list(names)
        if len(names) == 0:
            ghosts = topic_data.all_ghosts()
        else:
            ghosts = {name: topic_data.get_ghost(name) for name in names}
        return PublicChatOperator(
            topic=topic,
            hostname=self._hostname,
            message=message,
            ghosts=list(ghosts.values()),
        )

    def private_chat(self, topic: str, message: str, names: List[str]) -> Operator:
        pass

    def parallel_chat(self, topic: str, message: str, *names: str) -> Operator:
        pass

    def async_chat(self, topic: str, message: str, *names: str) -> Operator:
        pass

    def clear_topics(self, *topics: str) -> None:
        for topic in topics:
            self._clear_topic(topic)
        self._save_data()

    def _clear_topic(self, topic: str) -> None:
        if topic in self._data.topics:
            del self._data.topics[topic]
