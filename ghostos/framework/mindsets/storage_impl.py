from typing import Dict, Iterable, Type, Optional
import yaml
from ghostos.core.ghosts import Thought, ThoughtDriver
from ghostos.core.ghosts.thoughts import Mindset
from ghostos.contracts.storage import Storage
from ghostos.contracts.modules import Modules
from ghostos.helpers import generate_import_path, import_from_path
from ghostos.container import Provider, Container


class StorageMindset(Mindset):
    """
    基于 storage 来实现.
    """

    def __init__(self, storage: Storage, modules: Modules, namespace: str):
        self._modules = modules
        self._storage = storage
        self._cache_file = f"mindsets_{namespace}.cache.yml"
        self._thought_driver_map: Dict[Type[Thought], Type[ThoughtDriver]] = {}
        if self._storage.exists(self._cache_file):
            content = storage.get(self._cache_file)
            data = yaml.safe_load(content)
            self._thought_path_driver_path_map: Dict[str, str] = {}
            for key, val in data.items():
                if not isinstance(key, str) or not isinstance(val, str):
                    continue
                self._thought_path_driver_path_map[key] = val

    def register_thought_type(self, cls: Type[Thought], driver: Optional[Type[ThoughtDriver]] = None) -> None:
        if driver is None:
            driver = cls.default_driver_type()
        self._thought_driver_map[cls] = driver
        thought_type_path = generate_import_path(cls)
        thought_driver_type_path = generate_import_path(driver)
        self._thought_path_driver_path_map[thought_type_path] = thought_driver_type_path
        self._save_map()

    def _save_map(self) -> None:
        content = yaml.safe_dump(self._thought_path_driver_path_map)
        self._storage.put(self._cache_file, content.encode('utf-8'))

    def get_thought_driver_type(self, thought_type: Type[Thought]) -> Type[ThoughtDriver]:
        if thought_type in self._thought_driver_map:
            return self._thought_driver_map.get(thought_type)
        thought_type_path = generate_import_path(thought_type)
        if thought_type_path in self._thought_path_driver_path_map:
            driver_type_path = self._thought_path_driver_path_map[thought_type_path]
            result = import_from_path(driver_type_path, self._modules.import_module)
            if result is not None:
                return result
        return thought_type.default_driver_type()

    def thought_types(self) -> Iterable[Type[Thought]]:
        done = set()
        for thought_type in self._thought_driver_map:
            thought_type_path = generate_import_path(thought_type)
            done.add(thought_type_path)
            yield thought_type

        for thought_type_path in self._thought_path_driver_path_map:
            if thought_type_path not in done:
                done.add(thought_type_path)
                thought_type = import_from_path(thought_type_path, self._modules.import_module)
                yield thought_type


class StorageMindsetProvider(Provider):
    """
    mindset based by storage
    """

    def __init__(self, relative_path: str = "runtime/cache"):
        self._relative_path = relative_path

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Mindset]:
        return Mindset

    def factory(self, con: Container) -> Optional[Mindset]:
        storage = con.force_fetch(Storage)
        modules = con.force_fetch(Modules)
        cache_storage = storage.sub_storage(self._relative_path)
        return StorageMindset(cache_storage, modules, "")
