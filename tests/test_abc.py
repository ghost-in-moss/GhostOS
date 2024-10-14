from ghostos.common import PromptAble, PromptAbleClass
import inspect


def test_is_abstract():
    assert inspect.isabstract(PromptAble)
    assert inspect.isabstract(PromptAbleClass)
