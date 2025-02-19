from ghostos_container import Container
from ghostos.libraries.multighosts.abs_impl import BaseMultiGhosts
from ghostos.abcd import Session
from ghostos_moss import Injection
from ghostos.libraries.multighosts.data import MultiGhostData


class SessionLevelMultiGhostsImpl(BaseMultiGhosts):

    def _save_data(self):
        return None

    def self_prompt(self, container: Container) -> str:
        return f"""
Information about your ghosts and topics:

you saved ghosts: 
```yaml

```



"""

    def get_title(self) -> str:
        return "Your Multi Ghosts Library"
