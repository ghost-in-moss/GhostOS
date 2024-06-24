import os
from typing import List
from ghostiss.container import Container
from ghostiss.contracts.configs import YamlConfig, ConfigsByStorageProvider, Configs
from ghostiss.contracts.storage import FileStorageProvider


def test_configs():
    curr = os.path.dirname(__file__)
    container = Container()
    container.register(ConfigsByStorageProvider(""))
    container.register(FileStorageProvider(curr))

    configs = container.force_fetch(Configs)

    class FooConfig(YamlConfig):
        relative_path = "foo.yaml"

        foo: str
        bar: str
        arr: List[int]

    got = configs.get(FooConfig)
    assert got.foo == "foo"
    assert got.bar == "bar"
    assert got.arr == [1, 2, 3]
