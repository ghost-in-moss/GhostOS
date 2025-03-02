from typing import Optional
from ghostos.abcd import Session, get_ghost_identifier
from ghostos.libraries.multighosts.abcd import MultiGhosts
from ghostos.libraries.multighosts.abs_impl import BaseMultiGhosts
from ghostos.libraries.multighosts.data import MultiGhostData
from ghostos_common.helpers import yaml_pretty_dump
from ghostos_container import Container, Provider


class SessionLevelMultiGhostsImpl(BaseMultiGhosts):

    def _save_data(self):
        return None

    def self_prompt(self, container: Container) -> str:
        ghosts = {}
        for identity in self._data.ghosts.identities.values():
            ghosts[identity.name] = identity.description
        if ghosts:
            ghosts_yaml = yaml_pretty_dump(ghosts)
        else:
            ghosts_yaml = "empty"

        topics = []
        for topic in self._data.topics.values():
            topics.append(topic.dump_description())

        topics_yaml = "empty"
        if len(topics) > 0:
            topics_yaml = yaml_pretty_dump(topics)

        return f"""
Information about your ghosts and topics:

you saved ghosts (Dict[name, description]) are: 
```yaml
{ghosts_yaml}
```

you current topics (List[Dict]) are: 
```yaml
{topics_yaml}
```
"""

    def get_title(self) -> str:
        return "Your Multi Ghosts Library"


class SessionLevelMultiGhostsProvider(Provider[MultiGhosts]):
    """
    session level multi ghosts, all the data are bound to session.state
    """

    def __init__(self, session_state_key: str = "session_level_multi_ghosts"):
        self.session_state_key = session_state_key

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[MultiGhosts]:
        session = con.force_fetch(Session)
        if self.session_state_key not in session.state:
            data = MultiGhostData()
            # bind to session state
            session.state[self.session_state_key] = data
        data = session.state[self.session_state_key]
        hostname = get_ghost_identifier(session.ghost).name
        return SessionLevelMultiGhostsImpl(hostname=hostname, data=data)
