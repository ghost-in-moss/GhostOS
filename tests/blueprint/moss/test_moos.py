# import inspect
# from ghostiss.blueprint.moos.moos import count_source_indent, strip_source_indent, get_callable_definition
#
#
# class Foo:
#
#     def foo(self):
#         return self
#
#     @staticmethod
#     def bar():
#         return ""
#
#     @classmethod
#     def zoo(cls):
#         return cls
#
#     def cool(
#             self,
#             a: int,
#             b: str,
#     ) -> str:
#         return ""
#
#     def do(self) -> str:  # test
#         return ""
#
#     def doc(self) -> str:
#         """
#         test
#         """
#         return ""
#
#
# def test_count_source_indent():
#     source = inspect.getsource(Foo.foo)
#     f = Foo()
#     assert count_source_indent(source) == 4
#     assert count_source_indent(inspect.getsource(Foo.bar)) == 4
#     assert count_source_indent(inspect.getsource(f.zoo)) == 4
#
#
# def test_strip_source_indent():
#     f = Foo()
#     assert strip_source_indent(inspect.getsource(f.foo)).startswith("def foo(")
#     assert strip_source_indent(inspect.getsource(f.bar)).startswith("@staticmethod")
#     assert strip_source_indent(inspect.getsource(f.zoo)).startswith("@classmethod")
#
#
# def test_get_callable_definition():
#     f = Foo()
#     define = get_callable_definition(f.cool)
#     expect = """
# def cool(
#         self,
#         a: int,
#         b: str,
# ) -> str:
#     pass
# """
#     assert define == expect.strip()
#
#     define = get_callable_definition(f.bar)
#     expect = """
# @staticmethod
# def bar():
#     pass
# """
#     assert define == expect.strip()
#
#     define = get_callable_definition(f.foo)
#     expect = """
# def foo(self):
#     pass
# """
#     assert define == expect.strip()
#
#     define = get_callable_definition(Foo.do)
#     expect = """
# def do(self) -> str:  # test
#     pass
# """
#     assert define == expect.strip()
#
#     define = get_callable_definition(Foo.do, "test")
#     expect = """
# def test(self) -> str:  # test
#     pass
# """
#     assert define == expect.strip()
#
#     define = get_callable_definition(f.doc, "test")
#     expect = '''
# def test(self) -> str:
#     """
#     test
#     """
#     pass
# '''
#     assert define == expect.strip()
#
#     define = get_callable_definition(f.doc, "test", doc="hello\nworld")
#     expect = '''
# def test(self) -> str:
#     """
#     hello
#     world
#     """
#     pass
# '''
#     assert define == expect.strip()
