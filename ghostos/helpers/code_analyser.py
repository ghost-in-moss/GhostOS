from typing import List
from tree_sitter import (
    Node as TreeSitterNode,
)
from ghostos.helpers.tree_sitter import tree_sitter_parse

__all__ = ['get_code_interface', 'get_code_interface_str']


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
        return code[child.start_byte:child.end_byte]

    elif child.type == 'expression_statement':
        # 处理表达式语句
        return _get_assignment_interface(code, child)

    elif child.type == 'function_definition':
        # 处理函数定义
        func_name = child.child_by_field_name('name').text.decode()
        if func_name and not func_name.startswith('_'):
            docstring = get_node_docstring(child)
            definition = _get_full_definition(child, 0)

            func_interface = [definition]
            if docstring:
                func_interface.append(f'    """{docstring}"""')
            func_interface.append("    pass")
            return "\n".join(func_interface)

    elif child.type == 'class_definition':
        return _get_class_interface(code, child)

    elif child.type == 'decorated_definition':
        # 处理装饰器
        return _get_decorator_interface(code, child)

    else:
        return ""


def _get_decorator_interface(code: str, child: TreeSitterNode, depth: int = 0) -> str:
    decorator = child.children[0]
    definition = child.children[1]
    body = _get_child_interface_in_depth(code, definition, depth)
    decorator_interfaces = [(' ' * 4 * depth) + f"@{decorator.text.decode()}", body]
    return "\n".join(decorator_interfaces)


def _get_full_definition(child: TreeSitterNode, depth: int) -> str:
    children = child.children[1:len(child.children) - 1]
    definition = child.children[0].text.decode() + " "
    for child in children:
        definition += child.text.decode()
    return ' ' * 4 * depth + definition


def _get_assignment_interface(code: str, node: TreeSitterNode) -> str:
    expression = node.children[0]
    if expression.type != 'assignment':
        return ""

    # 处理赋值语句
    left = expression.children[0]
    right = expression.children[2]
    if left.type == 'identifier':
        var_name = code[left.start_byte:left.end_byte]
        if var_name.startswith('__') and var_name.endswith('__'):
            # 保持魔术变量和类型变量赋值原样
            return code[node.start_byte:node.end_byte]
        elif var_name.startswith('_') or var_name.startswith('__'):
            # 忽略私有变量赋值
            return ""
        else:
            # 如果赋值语句长度小于50个字符，保留原样
            assignment_code = code[node.start_byte:node.end_byte]
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
    class_definition = [_get_full_definition(class_node, 0)]

    # 处理类的 docstring
    docstring = get_node_docstring(class_node)
    if docstring:
        class_definition.append(f'    """{docstring}"""')

    class_interface = ["\n".join(class_definition)]
    # 处理类中的公共方法和__init__中的公共属性赋值
    property_count = 0
    class_body = class_node.children[-1]
    for class_child in class_body.children:

        if class_child.type == 'decorated_definition':
            # 处理装饰器
            decorator_interface = _get_decorator_interface(code, class_child, depth=1)
            class_interface.append(decorator_interface)

        elif class_child.type == 'function_definition':
            method_name = class_child.child_by_field_name('name').text.decode()
            if method_name == '__init__':
                init_method_interface = _get_class_init_body_interface(code, method_name, class_child)
                class_interface.append(init_method_interface)
            elif not method_name.startswith('_'):
                method_interface = _get_class_method_interface(method_name, class_child)
                class_interface.append(method_interface)
            property_count += 1
        # elif class_child.type == 'expression_statement':
        #     # 处理类的公共属性定义
        #     _get_assignment_interface(code, class_child)
        #     expr = class_child.children[0]
        #     if expr.type == 'assignment':
        #         left = expr.children[0]
        #         if left.type == 'identifier':
        #             var_name = code[left.start_byte:left.end_byte]
        #             if not (var_name.startswith('_') or var_name.startswith('__')):
        #                 class_interface.append(f"    {var_name} = ...")
        #                 property_count += 1
        else:
            interface = _get_child_interface_in_depth(code, class_child, 1)
            if interface:
                class_interface.append(interface)
                property_count += 1

    if property_count == 0:
        class_interface.append("    pass")
    return "\n\n".join(class_interface)


def _get_class_method_interface(method_name: str, method_node: TreeSitterNode) -> str:
    method_interface = [f"    def {method_name}(...):"]
    docstring = get_node_docstring(method_node)
    if docstring:
        method_interface.append(f'        """{docstring}"""')
    method_interface.append("        pass")
    return "\n".join(method_interface)


def _get_class_init_body_interface(code: str, method_name: str, method_node: TreeSitterNode) -> str:
    # 处理__init__方法中的公共属性赋值
    init_method_interface = [f"    def {method_name}(...):"]
    docstring = get_node_docstring(method_node)
    body_interface = []
    for init_child in method_node.children:
        if init_child.type == 'block':
            for block_child in init_child.children:
                if block_child.type == 'expression_statement':
                    expr = block_child.children[0]
                    if expr.type == 'assignment':
                        left = expr.children[0]
                        if left.type == 'attribute':
                            attr_name = code[left.start_byte:left.end_byte]
                            if not (attr_name.startswith('_') or attr_name.startswith('self._')):
                                body_interface.append(f"        {attr_name} = ...")
    body = "\n".join(body_interface)
    if docstring:
        init_method_interface.append(f'        """{docstring}"""')
    if body:
        init_method_interface.append(body)
    else:
        init_method_interface.append("        pass")

    return "\n".join(init_method_interface)


def get_node_docstring(node: TreeSitterNode) -> str:
    """
    获取函数或类的 docstring.
    """
    for child in node.children:
        if child.type == 'block':
            for block_child in child.children:
                if block_child.type == 'expression_statement':
                    expr = block_child.children[0]
                    if expr.type == 'string':
                        return expr.text.decode().strip().strip("'''").strip('"""')
    return ""
