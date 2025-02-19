from typing import List, Iterable, Optional
from ghostos.libraries.codex.abcd import ModuleInfo
from types import ModuleType
from ghostos_common.helpers import get_code_interface_str, yaml_pretty_dump
from ghostos.contracts.modules import Modules
import inspect


def generate_module_info(modulename: str, filename: str, source: str, is_pack: bool) -> Optional[ModuleInfo]:
    if not source:
        return None
    interface = get_code_interface_str(source)
    return ModuleInfo(
        name=modulename,
        file=filename,
        package=is_pack,
        interface=interface,
    )


def recursive_generate_module_infos(
        modules: Modules,
        root: ModuleType,
        is_pack: bool,
        ignore_error: bool = False,
) -> Iterable[ModuleInfo]:
    try:
        info = generate_module_info(root, is_pack)
        if info:
            yield info
    except OSError:
        pass
    except Exception as e:
        if not ignore_error:
            raise RuntimeError("recursive_generate_module_infos failed on %s" % root.__name__) from e

    if is_pack:
        for modulename, _is_pack in modules.iter_modules(root):
            module = modules.import_module(modulename)
            yield from recursive_generate_module_infos(modules, module, _is_pack, ignore_error)


def module_info_to_markdown(info: ModuleInfo) -> str:
    return f"""<module name=`{info.name}`>
```python
{info.interface}
```
</module>
"""


def dump_module_infos_to_markdown(infos: Iterable[ModuleInfo]) -> str:
    blocks = []
    for info in infos:
        blocks.append(module_info_to_markdown(info))
    return "\n\n".join(blocks)

# if __name__ == "__main__":
#     from ghostos_common import helpers
#     from ghostos.contracts.modules import DefaultModules
#
#     _modules = DefaultModules()
#
#     module_infos = recursive_generate_module_infos(_modules, helpers, True)
#     print(dump_module_infos_to_markdown(module_infos))
