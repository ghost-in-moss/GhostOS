from typing import Union
from ghostiss.core.moss.reflect import (
    reflect, )


def test_reflect_typing():
    test = Union[str, int, float]
    r = reflect(var=test, name="test")
    assert r.prompt() == "test = typing.Union[str, int, float]"
    # 验证真的可以用.
    assert isinstance(123, r.value())
