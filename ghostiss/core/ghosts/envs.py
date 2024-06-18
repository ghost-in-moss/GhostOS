from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Type
from ghostiss.entity import Normalized, EntityClass


class Envs(BaseModel):
    description: str = Field(default="", description="对 ghost 所处环境的描述.")
    trace: Dict = Field(default_factory=dict, description="通讯参数.")
    objects: List[Normalized] = Field(
        default_factory=list,
        description="环境中各种物体的元数据. 协议不对齐时, 无法理解环境.",
    )

    __objects: Optional[Dict[str, Normalized]] = None

    def __init(self):
        if self.__objects is not None:
            return
        self.__objects = {}
        for o in self.objects:
            self.__objects[o.kind] = o

    def get_meta(self, cls: Type[EntityClass]) -> Optional[EntityClass]:
        self.__init()
        data = self.get_object_meta(cls.entity_kind())
        if data is None:
            return None
        return cls.new_entity(data)

    def get_object_meta(self, meta_kind: str) -> Optional[Normalized]:
        self.__init()
        return self.__objects.get(meta_kind, None)
