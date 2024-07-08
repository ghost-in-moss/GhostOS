# from ghostiss.blueprint.moos.variable import (
#     get_caller_file, get_caller_module,
#     get_type,
#     PromptAbleClass, get_prompt,
# )
#
#
# def test_get_caller_file():
#     assert get_caller_file().endswith("test_variables.py")
#
#
# def test_get_caller_module():
#     assert get_caller_module().endswith("test_variables")
#
#
# def test_get_prompt():
#     class Foo(PromptAbleClass):
#
#         @classmethod
#         def get_prompt(cls):
#             return "Foo"
#
#     assert Foo.get_prompt is not None
#     assert get_prompt(Foo) == "Foo"
#     assert get_prompt(123) == ""
#     assert get_prompt(Foo()) == "Foo"
#
#
# def test_get_type():
#     assert get_type(123) is None
