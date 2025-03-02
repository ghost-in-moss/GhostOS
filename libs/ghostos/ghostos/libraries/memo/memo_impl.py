from typing import Dict, Optional

from ghostos.abcd import Session
from ghostos_container import Container, Provider, INSTANCE
from ghostos.libraries.memo.abcd import Memo
from ghostos_common.entity import EntityMeta, from_entity_meta, to_entity_meta
from pydantic import BaseModel, Field


class MemoData(BaseModel):
    watching: str = Field(default="", description="Watching code")
    descriptions: Dict[str, str] = Field(default_factory=dict, description="Description of memo objects")
    types: Dict[str, str] = Field(default_factory=dict, description="Types of memo objects")
    data: Dict[str, EntityMeta] = Field(default_factory=dict, description="Memo objects entity meta")


class MemoImpl(Memo):

    def __init__(self, data: MemoData):
        self._data = data

    def dump_context(self) -> str:
        keys = list(self._data.data.keys())
        keys_str = ""
        if len(keys) == 0:
            keys_str = "empty"
        else:
            for key in keys:
                desc = self._data.descriptions.get(key, "")
                desc = desc.replace("\n", " ")
                type_ = self._data.types.get(key, "")
                keys_str += f"\n`{key}`: ({type_}) {desc}"
            keys_str.lstrip()

        watching_code = self._data.watching if self._data.watching else "# empty"
        stdout = self.watch(watching_code) if self._data.watching else "empty"
        return f"""
The Context of the Memo are below:

defined keys (you can edit them by `memo.save` or `memo.remove`): 
```
{keys_str}
```

the watching code (you can change it by `memo.watching`): 
```python
{watching_code}
```

the stdout of the watching code:
```
{stdout}
```
"""

    def save(self, key: str, value: object, desc: str = None) -> None:
        if key in self._data.descriptions:
            if desc:
                self._data.descriptions[key] = desc
        else:
            self._data.descriptions[key] = desc or ""

        type_ = str(type(value))
        self._data.types[key] = type_
        self._data.data[key] = to_entity_meta(value)

    def get(self, key) -> Optional[object]:
        value = self._data.data.get(key, None)
        if value is None:
            return None
        return from_entity_meta(value)

    def remove(self, name: str) -> None:
        if name in self._data.descriptions:
            del self._data.descriptions[name]
        if name in self._data.types:
            del self._data.types[name]
        if name in self._data.data:
            del self._data.data[name]

    def values(self) -> Dict[str, object]:
        values = {}
        for key, meta in self._data.data.items():
            values[key] = from_entity_meta(meta)
        return values

    def _save_watch_code(self, code: str):
        self._data.watching = code

    def self_prompt(self, container: Container) -> str:
        return self.dump_context()

    def get_title(self) -> str:
        return "Memo details"


class SessionMemoProvider(Provider[Memo]):
    """
    session level memo
    bind the memo to the session.state
    """

    def __init__(self, session_state_key: str):
        self._session_state_key = session_state_key

    def singleton(self) -> bool:
        return False

    def factory(self, con: Container) -> Optional[INSTANCE]:
        session = con.force_fetch(Session)
        if self._session_state_key not in session.state:
            session.state[self._session_state_key] = MemoData()
        data = session.state[self._session_state_key]
        return MemoImpl(data)
