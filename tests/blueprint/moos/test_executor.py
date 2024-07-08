# from ghostiss.blueprint.moos.executor import execute
#
#
# def test_execute_baseline():
#     codes = """
# result__ = a + b
# """
#
#     r = execute(codes, a=5, b=5)
#     assert r == 10
#
#
# def test_execute_with_defined_var():
#     codes = """
# c = 123
#
# result__ = c == 123
# """
#
#     r = execute(codes, a=5, b=5)
#     assert r is True
#
#
# def test_execute_with_class_definition():
#     codes = """
# from abc import ABC
#
# class Interpreter(ABC):
#     pass
#
# result__ = Interpreter is not None
# """
#
#     r = execute(codes, a=5, b=5)
#     assert r is True
#
#
# def test_call_defined_class():
#     codes = """
# import time
#
# class Foo:
#     def foo(self):
#         return int(time.time())
#
#
# result__ = Foo().foo()
#     """
#
#     r = execute(codes, a=5, b=5)
#     assert isinstance(r, int)
#     assert r > 0
#
