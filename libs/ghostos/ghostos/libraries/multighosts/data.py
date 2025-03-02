from typing import Dict, List
from pydantic import BaseModel, Field
from ghostos.abcd import Ghost
from ghostos_common.entity import EntityMeta, to_entity_meta, from_entity_meta
from ghostos_common.identifier import Identifier, get_identifier
from ghostos_common.helpers import md5


class Topic(BaseModel):
    name: str = Field(description="topic name")
    description: str = Field(description="description")
    ghosts: Dict[str, EntityMeta] = Field(default_factory=dict, description="ghosts")
    logs: List[str] = Field(default_factory=list, description="logs")

    def thread_id(self, salt: str, ghost: str) -> str:
        return md5(f"topic:{self.name}:salt:{salt}:ghost:{ghost}")

    def add_ghosts(self, *ghosts: Ghost):
        for ghost in ghosts:
            id_ = get_identifier(ghost)
            self.ghosts[id_.name] = to_entity_meta(ghost)

    def get_ghost(self, name: str) -> Ghost:
        if name not in self.ghosts:
            raise KeyError(f"ghost {name} not found")
        meta = self.ghosts[name]
        return from_entity_meta(meta)

    def all_ghosts(self) -> Dict[str, Ghost]:
        data = {}
        for name in self.ghosts.keys():
            instance = self.get_ghost(name)
            data[name] = instance
        return data

    def dump_description(self) -> Dict:
        return dict(
            name=self.name,
            description=self.description,
            ghosts=[name for name in self.ghosts.keys()],
            logs=self.logs,
        )


class GhostsData(BaseModel):
    ghosts: Dict[str, EntityMeta] = Field(default_factory=dict, description="ghosts")
    identities: Dict[str, Identifier] = Field(default_factory=dict, description="identities")

    def add_ghosts(self, *ghosts: Ghost):
        for ghost in ghosts:
            id_ = get_identifier(ghost)
            self.ghosts[id_.name] = to_entity_meta(ghost)
            self.identities[id_.name] = id_

    def get_ghost(self, name: str) -> Ghost:
        ghost_meta = self.ghosts.get(name)
        if ghost_meta is None:
            raise KeyError(f"ghost {name} not found")
        return from_entity_meta(ghost_meta)


class MultiGhostData(BaseModel):
    ghosts: GhostsData = Field(default_factory=GhostsData, description="ghost data")
    topics: Dict[str, Topic] = Field(default_factory=dict, description="topic data")
