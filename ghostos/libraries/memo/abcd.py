from typing import List
from abc import ABC, abstractmethod


class Memo(ABC):
    """
    a tree like memo for you to save anything you want
    """

    _PATH = str
    """memo name in tree node path pattern separate by `.` . example: `foo.bar` """

    watching: List[_PATH]
    """the watching memo node paths, the contents of them are shown in the context"""

    @abstractmethod
    def dump_context(self) -> str:
        """
        dump memo context into a string. include:
        1. memo tree in Markdown list format.
        2. the watching memo node content
        """
        pass

    @abstractmethod
    def save(self, path: _PATH, desc: str = "", content: str = "") -> None:
        """
        add memo node to tree
        :param path: path of the node
        :param desc: description of the node, be shown in the node list. make it simple, clear in 100 words.
        :param content: the content of the node, shall not be too big.
        """
        pass

    @abstractmethod
    def remove(self, path: _PATH) -> None:
        """
        remove memo node from tree, include sub nodes.
        if the path is empty, means clear the memo tree.
        """
        pass

    @abstractmethod
    def move(self, path: _PATH, dest: _PATH) -> None:
        """
        move a memo node to new dest.
        :param path: the moving node path
        :param dest: destination path
        """
        pass
