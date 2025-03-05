from typing import List, Union, Dict
from tree_sitter import (
    Node as TreeSitterNode,
)
from ghostos_common.helpers.tree_sitter import tree_sitter_parse
from functools import lru_cache

__all__ = ['get_code_interface', 'get_code_interface_str', 'get_attr_source_from_code', 'get_attr_interface_from_code']


@lru_cache(maxsize=256)
def get_code_interface_str(code: str) -> str:
    return "\n\n".join(get_code_interface(code))


def get_code_interface(code: str) -> List[str]:
    try:
        # 解析代码，获取语法树
        tree = tree_sitter_parse(code)
        root_node = tree.root_node

        # 用于存储解析后的抽象描述
        interfaces = []
        for child in root_node.children:
            child_interface = _get_child_interface_in_depth(code, child, depth=0)
            if child_interface:
                interfaces.append(child_interface)

        return interfaces

    except Exception as e:
        # 异常处理
        raise


@lru_cache(maxsize=256)
def get_attr_source_from_code(code: str) -> Dict[str, str]:
    """
    get function or class attribute code.
    """
    try:
        data = {}
        # 解析代码，获取语法树
        tree = tree_sitter_parse(code)
        root_node = tree.root_node

        for child in root_node.children:
            name = _get_func_or_class_name(child)
            if name is not None:
                data[name] = child.text.decode()
        return data
    except Exception as e:
        # 异常处理
        raise


def get_attr_interface_from_code(code: str) -> Dict[str, str]:
    """
    get function or class interface map from the code.
    """
    data = {}
    # 解析代码，获取语法树
    tree = tree_sitter_parse(code)
    root_node = tree.root_node

    for child in root_node.children:
        name = _get_func_or_class_name(child)
        if name is not None:
            interface = _get_child_interface(code, child)
            if interface:
                data[name] = interface
    return data


def _get_func_or_class_name(child: TreeSitterNode) -> Union[str, None]:
    if child.type == 'function_definition':
        # 处理函数定义
        func_name = child.child_by_field_name('name').text.decode()
        return func_name
    elif child.type == 'class_definition':
        class_name = child.child_by_field_name('name').text.decode()
        return class_name

    elif child.type == 'decorated_definition':
        # 处理装饰器
        return _get_decorator_target_name(child)
    return None


def _get_decorator_target_name(child: TreeSitterNode) -> str:
    definition = child.children[1]
    return _get_func_or_class_name(definition)


def _get_child_interface_in_depth(code: str, node: TreeSitterNode, depth: int) -> str:
    interface = _get_child_interface(code, node)
    if interface and depth > 0:
        intend = ' ' * 4
        splits = [intend + content for content in interface.split('\n')]
        return '\n'.join(splits)
    return interface


def _get_child_interface(code: str, child: TreeSitterNode) -> str:
    if child.type == 'import_statement' or child.type == 'import_from_statement':
        # 如果是引用语句，保持原样
        return child.text.decode()

    elif child.type == 'expression_statement':
        # 处理表达式语句
        return _get_assignment_interface(code, child)

    elif child.type == 'function_definition':
        # 处理函数定义
        func_name = child.child_by_field_name('name').text.decode()
        if func_name and not func_name.startswith('_'):
            definition = _get_function_interface(child)
            return definition
        return ""

    elif child.type == 'class_definition':
        return _get_class_interface(code, child)

    elif child.type == 'decorated_definition':
        # 处理装饰器
        return _get_decorator_interface(code, child)
    else:
        return ""


def _get_decorator_interface(code: str, child: TreeSitterNode) -> str:
    decorator = child.children[0]
    definition = child.children[1]
    body = _get_child_interface_in_depth(code, definition, 0)
    if body:
        decorator_interfaces = [f"{decorator.text.decode()}", body]
        return "\n".join(decorator_interfaces)
    return ""


def _get_full_definition(node: TreeSitterNode, docstring: bool = True) -> str:
    definition = node.children[0].text.decode() + ' '
    for child in node.children[1:]:
        if child.type != "block":
            text = child.text.decode()
            if child.type == 'identifier':
                definition = definition.rstrip() + ' '

            definition += text
        else:
            if len(child.children) > 0 and docstring:
                doc_node = child.children[0]
                if doc_node.type == 'expression_statement' and doc_node.children[0].type == "string":
                    doc_node = doc_node.children[0]
                    doc = "\n".join([line.lstrip() for line in doc_node.text.decode().splitlines()])
                    doc = insert_depth_to_code(doc, 1)
                    definition += "\n" + doc
            break
    return definition.lstrip()


def _get_assignment_interface(code: str, node: TreeSitterNode) -> str:
    expression = node.children[0]
    if expression.type == 'string':
        return node.text.decode()

    elif expression.type != 'assignment':
        return ""

    # 处理赋值语句
    left = expression.children[0]
    right = expression.children[2]
    if left.type == 'identifier':
        var_name = left.text.decode()
        if var_name.startswith('__') and var_name.endswith('__'):
            # 保持魔术变量和类型变量赋值原样
            return node.text.decode()
        elif var_name.startswith('_') or var_name.startswith('__'):
            # 忽略私有变量赋值
            return ""
        else:
            # 如果赋值语句长度小于50个字符，保留原样
            assignment_code = node.text.decode()
            if len(assignment_code) < 500:
                return assignment_code
            else:
                # 折叠其它赋值
                return f"{var_name} = ..."


def _get_class_interface(code, class_node: TreeSitterNode) -> str:
    # 处理类定义
    class_name = class_node.child_by_field_name('name').text.decode()
    if class_name.startswith('_'):
        return ""
    class_definition = _get_full_definition(class_node, docstring=False)

    class_body_interface = []
    # 处理类中的公共方法和__init__中的公共属性赋值
    property_count = 0
    class_body = class_node.children[-1]
    for class_child in class_body.children:
        if class_child.type == 'decorated_definition':
            # 处理装饰器
            decorator_interface = _get_decorator_interface(code, class_child)
            class_body_interface.append(decorator_interface)

        elif class_child.type == 'function_definition':
            method_name = class_child.child_by_field_name('name').text.decode()
            if method_name == '__init__':
                init_method_interface = _get_class_init_body_interface(code, class_child)
                class_body_interface.append(init_method_interface)
            elif not method_name.startswith('_'):
                method_interface = _get_function_interface(class_child)
                class_body_interface.append(method_interface)
            property_count += 1
        else:
            interface = _get_child_interface_in_depth(code, class_child, 0)
            if interface:
                class_body_interface.append(interface)
                property_count += 1

    if property_count == 0:
        class_body_interface.append("    pass")
    class_body = "\n\n".join([itf for itf in class_body_interface if itf])
    class_body = insert_depth_to_code(class_body, 1)
    return class_definition + "\n" + class_body


def insert_depth_to_code(code: str, depth: int) -> str:
    if depth < 1:
        return code
    indent = ' ' * 4 * depth
    lines = []
    for line in code.splitlines():
        if line:
            line = indent + line
        lines.append(line)
    return '\n'.join(lines)


def _get_function_interface(method_node: TreeSitterNode) -> str:
    definition = _get_full_definition(method_node)
    method_interface = [definition, "    pass"]
    return "\n".join(method_interface)


def _get_class_init_body_interface(code: str, method_node: TreeSitterNode) -> str:
    # 处理__init__方法中的公共属性赋值
    definition = _get_full_definition(method_node)
    init_method_interface = [definition]
    body_interface = []
    for init_child in method_node.children:
        if init_child.type == 'block':
            for block_child in init_child.children:
                if block_child.type == 'expression_statement':
                    expr = block_child.children[0]
                    if expr.type == 'assignment':
                        left = expr.children[0]
                        if left.type == 'attribute':
                            attr_name = left.text.decode()
                            if not (attr_name.startswith('_') or attr_name.startswith('self._')):
                                expr_line = expr.text.decode()
                                if len(expr_line) > 50:
                                    expr_line = expr_line[:50] + "..."
                                body_interface.append(f"    {expr_line}")
    body = "\n".join(body_interface)
    if body:
        init_method_interface.append(body)
    else:
        init_method_interface.append("        pass")

    return "\n".join(init_method_interface)


def _get_node_docstring(node: TreeSitterNode) -> str:
    """
    获取函数或类的 docstring.
    """
    for child in node.children:
        if child.type == 'block':
            for block_child in child.children:
                if block_child.type == 'expression_statement':
                    expr = block_child.children[0]
                    if expr.type == 'string':
                        return expr.text.decode().strip()
    return ""
