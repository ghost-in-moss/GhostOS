def test_exec_read_source():
    from types import ModuleType
    code = """
def foo() -> str:
    return 'foo'
"""
    test = ModuleType('test_exec')
    exec(code, test.__dict__)

    from tree_sitter_languages import get_parser, get_language
    language = get_language('python')
    parser = get_parser('python')
    tree = parser.parse(code.encode('utf-8'))

    foo = tree.root_node.children[0]
    assert foo is not None
    assert foo.text == code.strip().encode('utf-8')

    # 我该怎么续写, 以获取 foo 方法的源码??

