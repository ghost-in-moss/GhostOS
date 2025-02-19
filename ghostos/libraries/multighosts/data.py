from typing import Dict
from pydantic import BaseModel, Field
from ghostos.abcd import Ghost
from ghostos.entity import EntityMeta, to_entity_meta, from_entity_meta
from ghostos.identifier import Identifier, get_identifier
from ghostos.helpers import md5


class Topic(BaseModel):
    name: str = Field(description="topic name")
    description: str = Field(description="description")
    ghosts: Dict[str, EntityMeta] = Field(description="ghosts")

    def thread_id(self, salt: str, ghost: str) -> str:
        return md5(f"topic:{self.name}:salt:{salt}:ghost:{ghost}")

    def add_ghosts(self, *ghosts: Ghost):
        for ghost in ghosts:
            id_ = get_identifier(ghost)
            self.ghosts[id_] = to_entity_meta(ghost)

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


class GhostsData(BaseModel):
    ghosts: Dict[str, EntityMeta] = Field(default_factory=dict, description="ghosts")
    identities: Dict[str, Identifier] = Field(default_factory=dict, description="identities")

    def add_ghosts(self, *ghosts: Ghost):
        for ghost in ghosts:
            id_ = get_identifier(ghost)
            self.ghosts[id_] = to_entity_meta(ghost)
            self.identities[id_] = id_


class MultiGhostData(BaseModel):
    ghosts: GhostsData = Field(default_factory=GhostsData, description="ghost data")
    topics: Dict[str, Topic] = Field(default_factory=dict, description="topic data")
