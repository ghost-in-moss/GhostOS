import inspect
from typing import List, Type, Dict, Set, Iterable, Optional
from types import ModuleType

from ghostos_common.identifier import Identifier, identify_class
from ghostos.core.aifunc import AIFunc, ExecFrame
from ghostos.core.aifunc.interfaces import AIFuncRepository
from ghostos.contracts.configs import YamlConfig, Configs
from ghostos.contracts.modules import Modules
from ghostos.contracts.storage import Storage
from ghostos.contracts.workspace import Workspace
from ghostos_common.helpers import generate_module_and_attr_name
from ghostos_container import Provider, Container
from pydantic import Field
from os.path import join
import time


class AIFuncsConf(YamlConfig):
    relative_path = "registered_aifunc.yml"

    identifiers: Dict[str, Identifier] = Field(
        default_factory=dict,
        description="registered AiFuncs identifier",
    )
    validated_at: int = Field(0, description="validate the identifiers, validation time in seconds")
    overdue: int = Field(3600, description="Overdue time in seconds")

    def is_overdue(self) -> bool:
        now = int(time.time())
        return now - self.validated_at > self.overdue


class AIFuncRepoByConfigs(AIFuncRepository):

    def __init__(
            self,
            conf: AIFuncsConf,
            configs: Configs,
            modules: Modules,
            frame_storage: Optional[Storage] = None,
    ):
        self.conf = conf
        self.configs = configs
        self.modules = modules
        if self.conf.is_overdue():
            self.validate()
        self.frame_storage = frame_storage

    def register(self, *fns: Type[AIFunc]) -> None:
        saving = []
        for fn in fns:
            if not issubclass(fn, AIFunc):
                raise TypeError(f"AiFunc must be subclass of AIFunc, not {fn}")
            identifier = identify_class(fn)
            saving.append(identifier)
        self._save_aifunc_identifier(*saving)

    def _save_aifunc_identifier(self, *identifiers: Identifier) -> None:
        for identifier in identifiers:
            self.conf.identifiers[identifier.id] = identifier
        self.configs.save(self.conf)

    def scan(self, module_name: str, *, recursive: bool, save: bool) -> List[Identifier]:
        mod = self.modules.import_module(module_name)
        result: Set[Type[AIFunc]] = set()
        self._scan_aifuncs_in_module(mod, result, recursive)
        returns = []
        for fn in result:
            if fn is AIFunc:
                continue
            identifier = self.identify(fn)
            returns.append(identifier)
        if save:
            self._save_aifunc_identifier(*returns)
        return returns

    def _scan_aifuncs_in_module(self, mod: ModuleType, scanned: Set[Type[AIFunc]], recursive: bool) -> None:
        """
        scan a single module, not recursively
        """
        for name in mod.__dict__:
            if name.startswith("_"):
                continue
            value = mod.__dict__[name]
            if value and inspect.isclass(value) and issubclass(value, AIFunc):
                scanned.add(value)
        for sub_module_name, is_pkg in self.modules.iter_modules(mod):
            try:
                sub_module = self.modules.import_module(sub_module_name)
                self._scan_aifuncs_in_module(sub_module, scanned, recursive)
            except Exception:
                continue

    def list(self, offset: int = 0, limit: int = -1) -> Iterable[Identifier]:
        limit = limit if limit > 0 else len(self.conf.identifiers)
        return list(self.conf.identifiers.values())[offset:offset + limit]

    def validate(self) -> None:
        identifiers = {}
        for key, val in self.conf.identifiers.items():
            modulename, attr_name = generate_module_and_attr_name(val.id)
            try:
                mod = self.modules.import_module(modulename)
                if key not in mod.__dict__:
                    continue
                attr = mod.__dict__[attr_name]
                if attr is not None and inspect.isclass(attr) and issubclass(attr, AIFunc):
                    identifiers[key] = val
            except ModuleNotFoundError:
                continue
        self.conf.identifiers = identifiers
        self.configs.save(self.conf)

    def save_exec_frame(self, frame: ExecFrame) -> None:
        if self.frame_storage is not None:
            filename = self._frame_filepath(frame.func_name(), frame.frame_id + ".json")
            value = frame.model_dump_json(exclude_defaults=True, indent=2)
            self.frame_storage.put(filename, value.encode())
        return None

    @classmethod
    def _frame_filepath(cls, func_name: str, frame_id: str, ext: str = ".json") -> str:
        return join(func_name, frame_id + ext)


class AIFuncRepoByConfigsProvider(Provider[AIFuncRepository]):

    def __init__(self, runtime_frame_dir: str = "aifunc_frames"):
        self._runtime_frame_dir = runtime_frame_dir

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[AIFuncRepository]:
        configs = con.force_fetch(Configs)
        modules = con.force_fetch(Modules)
        conf = configs.get(AIFuncsConf)
        conf.validated_at = int(time.time())
        runtime_storage = None
        if self._runtime_frame_dir:
            workspace = con.force_fetch(Workspace)
            runtime_storage = workspace.runtime().sub_storage(self._runtime_frame_dir)
        return AIFuncRepoByConfigs(conf, configs, modules, runtime_storage)
