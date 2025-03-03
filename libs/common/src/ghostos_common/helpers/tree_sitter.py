from typing import Optional, Iterable, List, Set, Dict, Type, ClassVar, Generator
from abc import ABC, abstractmethod
from tree_sitter import (
    Tree, Node as TreeSitterNode,
)
from enum import Enum
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

_PythonParser = None

__all__ = [
    'tree_sitter_parse', 'code_syntax_check', 'traverse_tree', 'get_error_nodes', 'get_node_error',
    'TreeSitterNode', 'TreeNodeType',
    'PyNode', 'PyClassNode', 'PyAttrNode', 'PyImportNode', 'PyModuleNode', 'PyStrNode',
]


def tree_sitter_parse(code: str) -> Tree:
    global _PythonParser
    if _PythonParser is None:
        PY_LANGUAGE = Language(tspython.language())
        _PythonParser = Parser(PY_LANGUAGE)
    return _PythonParser.parse(code.encode())


def code_syntax_check(code: str) -> Optional[str]:
    """
    check code syntax correctness.
    :param code:
    :return:
    """
    try:
        tree = tree_sitter_parse(code)
    except Exception as e:
        return f"parse code failed: {e}"

    errors = []
    travel_node_error(code, tree.root_node, errors)
    if errors:
        return "- " + "\n- ".join(errors)
    return None


def traverse_tree(tree: Tree) -> Generator[TreeSitterNode, None, None]:
    """
    simplify traversal of tree.
    :param tree:
    :return:
    """
    cursor = tree.walk()

    visited_children = False
    while True:
        if not visited_children:
            yield cursor.node
            if not cursor.goto_first_child():
                visited_children = True
        elif cursor.goto_next_sibling():
            visited_children = False
        elif not cursor.goto_parent():
            break


def travel_node_error(code: str, node: TreeSitterNode, errors: List[str]) -> None:
    error = get_node_error(code, node)
    if error is not None:
        errors.append(error)
        return
    for child in node.children:
        travel_node_error(code, child, errors)


def get_node_error(code: str, node: TreeSitterNode) -> Optional[str]:
    """
    get all the errors when traversing a node
    """
    if node.is_error:
        start_point_row, col = node.start_point
        line_number = start_point_row + 1
        line_content = code.splitlines()[line_number - 1]
        # 这里假设错误分析就是节点的类型和文本内容
        return f"Syntax Error at line {line_number}: `{line_content}`"
    return None


def get_error_nodes(node: TreeSitterNode) -> Iterable[TreeSitterNode]:
    def traverse_tree_for_errors(_node: TreeSitterNode):
        for n in _node.children:
            if n.type == "ERROR" or n.is_missing:
                yield n
            if n.has_error:
                # there is an error inside this node let's check inside
                yield from traverse_tree_for_errors(n)

    yield from traverse_tree_for_errors(node)


def parse_error(root_node: TreeSitterNode, error_type: str = "SYNTAX_ERROR"):
    padding = " " * 5
    lines = []
    # todo


class TreeNodeType(str, Enum):
    IDENTIFIER = 'identifier'
    COLON = ':'
    DECORATED = 'decorated_definition'
    EXPRESSION_STATEMENT = 'expression_statement'


class PyNode(ABC):
    type: ClassVar[str]

    def __init__(self, source: str, node: Optional[TreeSitterNode] = None, depth: int = 0):
        self._source = source
        self._tree_sitter_node: Optional[TreeSitterNode] = node
        self._depth = depth
        self._children: Optional[List[PyNode]] = None

    def depth(self) -> int:
        return self._depth

    @classmethod
    @abstractmethod
    def type(cls) -> str:
        pass

    def has_error(self) -> bool:
        return self.tree_sitter_node().has_error

    @classmethod
    def new(cls, node: TreeSitterNode, depth: int, source: str = "") -> "PyNode":
        if not source:
            source = str(node.text)
        return cls(source, node, depth)

    def indent(self) -> str:
        return "    " * self.depth()

    def tree_sitter_node(self) -> TreeSitterNode:
        if self._tree_sitter_node is None:
            parsed = tree_sitter_parse(self._source)
            self._tree_sitter_node = parsed.root_node
        return self._tree_sitter_node

    def source(self) -> str:
        return self._source

    @abstractmethod
    def children(self) -> Iterable["PyNode"]:
        pass


class PyClassNode(PyNode):
    type: ClassVar[str] = "class_definition"

    _identifier: Optional[str] = None
    _definition: Optional[str] = None
    _doc: Optional[str] = None

    def identifier(self) -> str:
        if self._identifier:
            return self._identifier
        identifier = ""
        if not self.has_error():
            for node in self.tree_sitter_node().named_children:
                if node.type == TreeNodeType.IDENTIFIER.value:
                    identifier = str(node.text)
                    break
        self._identifier = identifier
        return self._identifier

    def definition(self) -> str:
        if self._definition is not None or self.has_error():
            return self._definition if self._definition else ""
        parts = []
        for node in self.tree_sitter_node().children:
            if node.type == TreeNodeType.COLON.value:
                break
            parts.append(str(node.text))
        definition = ' '.join(parts)
        self._definition = definition + ':'
        return self._definition

    def _block(self) -> Optional[TreeSitterNode]:
        if self.has_error():
            return None
        return self.tree_sitter_node().children[-1]

    def children(self) -> Iterable["PyNode"]:
        if self.has_error():
            return []
        if self._children is not None:
            return self._children if self._children else []
        block = self._block()
        if block is None:
            self._children = []
            return self._children
        children = []
        depth = self.depth() + 1
        for child in block.children:
            wrapped = wrap_named_child(child, "", depth)
            if wrapped is not None:
                children.append(wrapped)
        self._children = children
        return self._children

    def classes(self) -> Iterable["PyClassNode"]:
        pass

    def doc(self) -> str:
        children = list(self.children())[0]
        if isinstance(children, PyStrNode):
            return children.source()
        return ""

    def methods(self) -> Iterable["PyMethodNode"]:
        for child in self.children():
            if isinstance(child, PyMethodNode):
                yield child

    def attrs(self) -> Iterable["PyAttrNode"]:
        for child in self.children():
            if isinstance(child, PyMethodNode):
                yield child

    def is_public(self) -> bool:
        return not self.identifier().startswith('_')

    def generate_code(
            self, *,
            definition: Optional[str] = None,
            doc: Optional[str] = None,
            body: bool = True,
            includes: Optional[Set[str]] = None,
            excludes: Optional[Set[str]] = None,
            public_only: bool = True,
    ) -> str:
        return self.source()


class PyImportNode(PyNode):
    type = 'import_from_statement'

    def __init__(self, source: str, node: Optional[TreeSitterNode] = None, depth: int = 0):
        self._module: str = ""
        self._species: List[str] = []
        self._aliases: Dict[str, str] = {}
        self._attr_names: List[str] = []
        super().__init__(source, node, depth)

    def _parse(self):
        if self._module:
            # 解析完成.
            return
        node = self.tree_sitter_node()
        if node.has_error:
            return

        spec = ""
        alias_name = ""
        for child in node.named_children:
            if child.type == "dotted_name":
                # 第一个一定得是 module.
                if self._module is None:
                    self._module = str(child.text)
                    continue
                elif spec:
                    self._species.append(spec)
                    if alias_name:
                        self._aliases[alias_name] = spec
                    self._attr_names.append(alias_name if alias_name else spec)
                    alias_name = ""
                    spec = str(child.text)
            elif child.type == "aliased_import":
                text = str(child.text)
                alias_name = text.split(' ')[-1]
            else:
                continue
        if spec:
            self._species.append(spec)
            if alias_name:
                self._aliases[alias_name] = spec
            self._attr_names.append(alias_name if alias_name else spec)
        return

    def modulename(self) -> str:
        self._parse()
        return self._module

    def attr_names(self) -> Iterable[str]:
        self._parse()
        yield from self._attr_names

    def specs(self) -> Iterable[str]:
        self._parse()
        yield from self._species

    def aliases(self) -> Dict[str, str]:
        self._parse()
        return self._aliases.copy()

    def children(self) -> Iterable["PyNode"]:
        return []


class PyMethodNode(PyNode):
    def identifier(self) -> str:
        pass

    def definition(self) -> str:
        pass

    def doc(self) -> str:
        pass

    def body(self) -> str:
        pass

    def generate_code(
            self, *,
            identifier: Optional[str] = None,
            definition: Optional[str] = None,
            doc: Optional[str] = None,
            body: bool = True,
    ) -> str:
        pass


class PyAttrNode(PyNode):
    def identifier(self) -> str:
        pass

    def is_string(self) -> bool:
        source = self._source.rstrip()
        if not len(source) > 2:
            return False
        start = source[0]
        end = source.rstrip()[-1]
        quotes = {'"', "'"}
        if start in quotes and end in quotes:
            return True
        return False

    def is_public(self) -> bool:
        return not self.identifier().startswith('_')

    def doc(self) -> str:
        pass


class PyModuleNode(PyNode):
    type = "module"

    def classes(self) -> Iterable["PyClassNode"]:
        for child in self.children():
            if isinstance(child, PyClassNode):
                yield child

    def attrs(self) -> Iterable["PyAttrNode"]:
        for child in self.children():
            if isinstance(child, PyAttrNode):
                yield child

    def functions(self) -> Iterable["PyMethodNode"]:
        for child in self.children():
            if isinstance(child, PyMethodNode):
                yield child

    def children(self) -> Iterable["PyNode"]:
        if self.has_error():
            return []
        if self._children is None:
            depth = self.depth() + 1
            children = []
            for child in self.tree_sitter_node().named_children:
                wrapped = wrap_named_child(child, "", depth)
                if wrapped is not None:
                    children.append(wrapped)
            self._children = children
        return self._children

    def generate_code(
            self, *,
            classes: Optional[Set[str]] = None,
            methods: Optional[Set[str]] = None,
            attrs: Optional[Set[str]] = None,
            excludes: Optional[Set[str]] = None,
            public_only: bool = True,
    ) -> str:
        pass


class PyStrNode(PyNode):
    type = 'string'

    def children(self) -> Iterable["PyNode"]:
        return []


def wrap_named_child(node: TreeSitterNode, source: str = "", depth: int = 0) -> Optional[PyNode]:
    if node.type == TreeNodeType.DECORATED.value or node.type == TreeNodeType.EXPRESSION_STATEMENT.value:
        source = source if source else str(node.text)
        sub_node = node.children[0].children[-1]
        return wrap_named_child(sub_node, source, depth)
    elif node.type in PythonNodeMap:
        wrapper = PythonNodeMap.get(node.type, None)
        if wrapper is not None:
            return wrapper.new(node, depth, source)
    return None


PythonNodeMap: Dict[str, Type[PyNode]] = {
    PyModuleNode.type: PyModuleNode,
    PyClassNode.type: PyClassNode,
    PyImportNode.type: PyImportNode,
    PyMethodNode.type: PyMethodNode,
    PyAttrNode.type: PyAttrNode,
    PyStrNode.type: PyStrNode,
}
