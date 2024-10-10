from typing import List
from ghostos.contracts.configs import Config, YamlConfig
from ghostos.framework.configs import MemoryConfigs


class FooConf(YamlConfig):
    relative_path = "hello.yml"
    foo: str = "abc"
    bar: float = 1.1


def test_config_marshal():
    cases: List[Config] = [
        FooConf(),
    ]

    configs = MemoryConfigs()

    for c in cases:
        marshaled = c.marshal()
        un_marshaled = c.unmarshal(marshaled)
        marshaled2 = un_marshaled.marshal()
        assert marshaled == marshaled2, c

        configs.save(c)
        got = configs.get(type(c))
        assert got.marshal() == marshaled
