from typing import Optional

from ghostos.container import Provider, Container, INSTANCE
from ghostos.contracts.modules import Modules
from ghostos.entity import EntityFactory, EntityFactoryImpl


class EntityFactoryProvider(Provider[EntityFactory]):
    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[EntityFactory]:
        modules = con.force_fetch(Modules)
        return EntityFactoryImpl(modules.import_module)
