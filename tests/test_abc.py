from ghostos.common import Prompter, PrompterClass
import inspect


def test_is_abstract():
    assert inspect.isabstract(Prompter)
    assert inspect.isabstract(PrompterClass)
