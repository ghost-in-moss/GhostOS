from typing import List, Optional
from typing_extensions import Self

from ghostos.abcd import Session, StateValue
from ghostos.libraries.pyeditor.abcd import PyInspector
from ghostos.core.moss import Injection, MossRuntime
from ghostos.contracts.modules import Modules
from ghostos.helpers import generate_import_path, import_from_path, get_code_interface_str
from ghostos.container import Container, Provider
from pydantic import BaseModel, Field
import inspect


class Inspecting(BaseModel, StateValue):
    property_name: str = Field()
    watching_source: List[str] = Field(default_factory=list)
    watching_interface: List[str] = Field(default_factory=list)

    def get(self, session: Session) -> Optional[Self]:
        pass

    def bind(self, session: Session) -> None:
        pass


class PyInspectorSessionImpl(Injection, PyInspector):

    def __init__(
            self,
            session: Session,
            modules: Modules,
    ):
        self.reading_source = []
        self.reading_interface = []
        self._modules = modules
        self._property_name = generate_import_path(self.__class__)
        self._session: Session = session

    def on_inject(self, runtime: MossRuntime, property_name: str) -> Self:
        self._property_name = property_name
        bound = self._get_inspecting()
        self.reading_source = bound.watching_source
        self.reading_interface = bound.watching_interface
        return self

    def _get_inspecting(self) -> Inspecting:
        return Inspecting(
            property_name=self._property_name,
            watching_source=list(set(self.reading_source)),
            watching_interface=list(set(self.reading_interface)),
        )

    def on_destroy(self) -> None:
        inspecting = self._get_inspecting()
        inspecting.bind(self._session)

    def get_source(self, import_path: str) -> str:
        try:
            imported = import_from_path(import_path, self._modules.import_module)
            return inspect.getsource(imported)
        except Exception as e:
            return f"# failed to get source for `{import_path}`: {e}"

    def get_interface(self, import_path: str) -> str:
        try:
            imported = import_from_path(import_path, self._modules.import_module)
            source = inspect.getsource(imported)
            return get_code_interface_str(source)
        except Exception as e:
            return f"# failed to get interface for `{import_path}`: {e}"

    def dump_context(self) -> str:
        source_code_context = ""
        for inspecting in self.reading_source:
            source_code = self.get_source(inspecting)
            source_code_context += f"""
- `{inspecting}`:
```python
{source_code}
```
"""
        interface_context = ""
        for inspecting in self.reading_interface:
            interface = self.get_interface(inspecting)
            interface_context += f"""
- `{inspecting}`:
```python
{interface}
```
"""

        return f"""
With PyInspector you can read code information.

The source code that you are inspecting are: 

<inspecting-source-code>
{source_code_context or "empty"}
</inspecting-source-code>


The interface that you are inspecting are:

<inspecting-interface>
{interface_context or "empty"}
</inspecting-interface>

"""

    def self_prompt(self, container: Container) -> str:
        return self.dump_context()

    def get_title(self) -> str:
        return "PyInspector Context"


class SimplePyInspectorProvider(Provider[PyInspector]):

    def singleton(self) -> bool:
        return False

    def factory(self, con: Container) -> Optional[PyInspector]:
        session = con.force_fetch(Session)
        modules = con.force_fetch(Modules)

        return PyInspectorSessionImpl(
            session=session,
            modules=modules,
        )
