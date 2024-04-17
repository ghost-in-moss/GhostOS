from typing import List
from abc import ABC
from pydantic import BaseModel


class Ghost(ABC):
    memories: List
    mindset: List
    tools: List
