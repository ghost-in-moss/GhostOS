from typing import Optional, Type, Union, Any, TypeVar

from pydantic import BaseModel

from ghostos.contracts.variables import Variables
from ghostos.contracts.storage import Storage
from ghostos.contracts.workspace import Workspace
from ghostos_common.entity import EntityType, to_entity_meta, from_entity_meta, EntityMeta
from ghostos_common.identifier import try_get_identifier
from ghostos_common.helpers import md5, generate_import_path, uuid
from ghostos_container import Provider, Container
import json

T = TypeVar("T")


class VariablesImpl(Variables):

    def __init__(self, storage: Storage):
        self.storage = storage

    def save(
            self,
            val: Union[BaseModel, dict, list, str, int, float, bool, EntityType, Any],
            desc: str = "",
    ) -> Variables.Var:
        if isinstance(val, Variables.Var):
            return val
        entity_meta = to_entity_meta(val)
        type_ = generate_import_path(type(val))
        id_ = try_get_identifier(val)
        if id_ is not None and id_.id:
            vid = md5(type_ + "::" + id_.id)
        else:
            vid = uuid()
        var = Variables.Var(
            vid=vid,
            type=type_,
            desc=desc,
        )
        content = json.dumps(entity_meta)
        filename = self._get_filename(vid)
        self.storage.put(filename, content.encode())
        return var

    @staticmethod
    def _get_filename(vid: str) -> str:
        return f"{vid}.var.json"

    def load(self, vid: str, expect: Optional[Type[T]] = None, force: bool = False) -> Optional[T]:
        filename = self._get_filename(vid)
        if not self.storage.exists(filename):
            if not force:
                return None
            else:
                raise FileNotFoundError(f"variable {vid} not found at: {filename}")
        content = self.storage.get(filename)
        data = json.loads(content)
        entity_meta = EntityMeta(**data)
        entity = from_entity_meta(entity_meta)
        if expect and not isinstance(entity, expect):
            raise ValueError(f"variable {vid} expect {expect} but got {type(entity)}")
        return entity


class WorkspaceVariablesProvider(Provider[Variables]):

    def __init__(self, relative_path: str = "variables"):
        self.relative_path = relative_path

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[Variables]:
        ws = con.force_fetch(Workspace)
        storage = ws.runtime().sub_storage(self.relative_path)
        return VariablesImpl(storage)
