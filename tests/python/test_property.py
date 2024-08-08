class Property:

    def __init__(self):
        self.count = 0
        self.value = []

    def __set__(self, instance, value):
        self.count += 1

    def __get__(self, instance, owner) -> list:
        self.count += 1
        return self.value


def test_property_assign():
    prop = Property()

    class Foo:
        p = prop

    f = Foo()
    assert f.p == []
    f.p.append(1)
    assert f.p == [1]
    assert prop.count == 3
