from abc import ABC, abstractmethod
from typing import List, Dict, Iterable, Optional
from ghostos.libraries.memo.abcd import Memo
from pydantic import BaseModel, Field


class MemoNode(BaseModel):
    path: str = Field(default="", description="the path of the memo node in filename pattern, like 'path.path.name'")
    desc: str = Field(default="", description="the description of the memo node")
    content: str = Field(default="", description="the content of memo node")

    def name(self) -> str:
        return self.path.split(".")[-1]


class MemoNodeTree:

    def __init__(self, node: MemoNode, depth: int = 0):
        self.node = node
        self.depth = depth
        self.children: Dict[str, MemoNodeTree] = {}

    @classmethod
    def new_root(cls) -> 'MemoNodeTree':
        return MemoNodeTree(MemoNode())

    def get_child(self, path: str) -> Optional['MemoNodeTree']:
        parts = path.rsplit(".", 1)
        if len(parts) != 2:
            return None
        if parts[0] not in self.children:
            return None
        key = parts[0]
        _next = parts[1]
        child = self.children[key]
        if not _next:
            return child
        return child.get_child(_next)

    def add_child(self, path: List[str], node: MemoNode) -> None:
        if len(path) == 0:
            self.children[node.name()] = node
            return

        child_name = path[0]
        if not child_name:
            return

        next_paths = path[1:]
        if child_name not in self.children:
            child_path = self.node.path + '.' + child_name
            child_path = child_path.strip().strip('.')
            self.children[child_name] = MemoNodeTree(
                MemoNode(path=child_path),
                depth=self.depth + 1,
            )
        child = self.children[child_name]
        child.add_child(next_paths, node)

    def add_node(self, node: MemoNode):
        path = node.path.split('.')
        self.add_child(path, node)

    def is_branch(self) -> bool:
        return len(self.children) > 0

    def list_nodes(self) -> Iterable[MemoNode]:
        if self.node.path:
            yield self
        for child in self.children.values():
            yield from child.list_nodes()


def markdown_list_item(node: MemoNode) -> str:
    mark = '+' if node.is_branch() else '-'
    indent = ' ' * 2 * node.depth
    desc = node.node.desc.replace('\n', ' ')
    desc_str = ': ' + desc if desc else ''
    name = node.node.name
    return f'{indent}{mark} `{name}`{desc_str}'


class MemoData(BaseModel):
    watching: List[str] = Field(default_factory=list)
    nodes: Dict[str, MemoNode] = Field(default_factory=list)


class AbsMemo(Memo, ABC):
    _node_tree: Optional[MemoNodeTree] = None

    @abstractmethod
    def _get_data(self) -> MemoData:
        pass

    @abstractmethod
    def _save_data(self, data: MemoData):
        pass

    @abstractmethod
    def dump_context(self) -> str:
        pass

    def _get_node_tree(self):
        if self._node_tree is None:
            data = self._get_data()
            self._node_tree = self._build_node_tree(data.nodes)
        return self._node_tree

    @staticmethod
    def _build_node_tree(nodes: Dict[str, MemoNode]) -> MemoNodeTree:
        _node_tree = MemoNodeTree.new_root()
        for node in nodes.values():
            _node_tree.add_node(node)
        return _node_tree

    def save(self, path: str, desc: str = "", content: str = "") -> None:
        node = MemoNode(path=path, desc=desc, content=content)
        data = self._get_data()
        data.nodes[node.path] = node
        self._node_tree = self._build_node_tree(data)
        self._save_data(data)

    def remove(self, path: str) -> None:
        data = self._remove(path)
        if data:
            self._save_data(data)
            self._node_tree = self._build_node_tree(data)

    def _remove(self, path: str) -> Optional[MemoData]:
        tree = self._get_node_tree()
        child = tree.get_child(path)
        if not child:
            return None
        data = self._get_data()
        for node in child.list_nodes():
            if node.path in data.nodes:
                del data.nodes[node.path]
        return data

    def move(self, path: str, dest: str) -> None:
        child = self._get_data()
        data = self._remove(path)
        if data is None or child is None:
            return
        tree = self._build_node_tree(data)
        for node in child.list_nodes():
            if node.path.startswith(path):
                node.path = dest + node.path[len(path):]
                tree.add_node(node)
                data.nodes[node.path] = node

        self._node_tree = tree
        self._save_data(data)
