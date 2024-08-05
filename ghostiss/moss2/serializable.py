from typing import Union, TypedDict
from pydantic import BaseModel
from ghostiss.entity import EntityClass, EntityMeta

Serializable = Union[int, str, float, bool, list, dict, None, BaseModel, TypedDict]
