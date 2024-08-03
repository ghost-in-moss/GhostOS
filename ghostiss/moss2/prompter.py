from typing import Dict, Any, Optional, Iterable
from ghostiss.moss2.reflection import Reflection
from dataclasses import dataclass


class Prompter:
    """
    Prompter that can generate moss reflection from values.
    """

    def reflect(self, *types, **named_attrs) -> "Prompter":
        pass

    def get(self, name: str) -> Optional[Reflection]:
        pass

    def reflections(self) -> Iterable[Reflection]:
        pass

    def all(self) -> Dict[str, Any]:
        pass
