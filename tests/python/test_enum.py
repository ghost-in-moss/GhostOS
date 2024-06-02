from enum import Enum


def test_enum_with_value():
    class Foo(str, Enum):
        BAR = "bar"

        def plus(self, value: str) -> str:
            return self + value

    # 判断是不是可以控制枚举值类型.
    assert Foo.BAR == "bar"
    assert Foo.BAR.plus('2') == 'bar2'
    # 但类型应该是 str, 不再是 enum 了.
    assert isinstance(Foo.BAR.plus('2'), str)
    assert not isinstance(Foo.BAR.plus('2'), Foo)

    assert Foo.BAR.name == "BAR"
    assert Foo.BAR.value == "bar"
