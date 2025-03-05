from abc import ABC, abstractmethod
from ghostos_common.prompter import PromptObjectModel

"""
这里设计一个简单的笔记抽象给 Agent.
Agent 可以将它需要的记忆记录到 Notebook 里. 
Notebook 通过树状的数据结构查看和展示内容. 

这个 notebook 用来做冷启动, 未来让模型自己设计自己使用的工具. 
"""


class Notebook(PromptObjectModel, ABC):
    """
    the simple notebook for you to record almost everything.
    tree_notes: use tree to align the notes. only the tree shall be shown up to you, you need to read them manually
    each node of the tree is a note.
    you shall use the branch node as category, and leaf node as note.
    """

    @abstractmethod
    def add_memo(self, topic: str, title: str, content: str = "", priority: float = 0.0) -> None:
        """
        add new memo content.
        :param topic: the topic of the memo
        :param title: the title of this memo, and also unique key
        :param content: content of the memo
        :param priority: the priority of the memo, from 0.0 to 1.0
        """
        pass

    @abstractmethod
    def save_note(self, path: str, desc: str, content: str) -> None:
        """
        :param path: the path to save the note, in the filename pattern `path_a/path_b/path_c`
        :param desc: description of the note for you to recall. summary of the content in less than 100 words.
        :param content: the content of your note.
        :return:
        """
        pass

    @abstractmethod
    def read_note(self, path: str) -> str:
        """
        read notes by path.
        :param path: in the filename pattern.
        :return:
        """
        pass

    @abstractmethod
    def move_note(self, path: str, new_path: str) -> None:
        """
        move the notes by path.
        :param path:
        :param new_path:
        """
        pass

    @abstractmethod
    def remove_note(self, path: str) -> bool:
        """
        :param path: the path of the note
        """
        pass

    @abstractmethod
    def list_notes_tree(self, prefix: str = '', depth: int = 3) -> str:
        """
        list the notes desc
        :param prefix: the root node path of the listed tree
        :param depth: the depth of the listed nodes from the prefix node.
        :return: the notes description.
        """
        pass
