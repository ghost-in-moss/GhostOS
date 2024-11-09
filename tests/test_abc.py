from ghostos.identifier import PromptAbleObj, PromptAbleClass
import inspect


def test_is_abstract():
    assert inspect.isabstract(PromptAbleObj)
    assert inspect.isabstract(PromptAbleClass)
