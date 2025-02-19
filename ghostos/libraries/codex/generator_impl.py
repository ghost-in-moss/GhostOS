from typing import Dict

from ghostos.libraries.codex.abcd import PyCodexGenerator, ModuleInfo
from ghostos.libraries.codex.utils import recursive_generate_module_infos
from ghostos_common.helpers import yaml_pretty_dump
from ghostos.contracts.modules import Modules
import yaml


class PyCodexGeneratorImpl(PyCodexGenerator):

    def __init__(self, modules: Modules):
        self._modules = modules

    def generate(self, root_module: str, ignore_error: bool = False) -> Dict[str, ModuleInfo]:
        root = self._modules.import_module(root_module)
        result = {}
        for info in recursive_generate_module_infos(self._modules, root, True, ignore_error):
            result[info.name] = info
        return result

    def dump_yaml(self, modules: Dict[str, ModuleInfo]) -> str:
        data = {}
        for key, info in modules.items():
            data[key] = info.model_dump(exclude_defaults=True)
        return yaml_pretty_dump(data)

    def from_yaml(self, content: str) -> Dict[str, ModuleInfo]:
        data = yaml.safe_load(content)
        module_infos = {}
        for key, value in data.items():
            info = ModuleInfo(**value)
            module_infos[key] = info
        return module_infos


if __name__ == "__main__":
    from ghostos.contracts.modules import DefaultModules

    pcg = PyCodexGeneratorImpl(DefaultModules())
    try:
        infos = pcg.generate("ghostos")
        content = pcg.dump_yaml(infos)
        print("++++++++")
        with open('codex.yaml', 'w') as f:
            f.write(content)
    except Exception as e:
        print("+++++++++++=", str(e))
