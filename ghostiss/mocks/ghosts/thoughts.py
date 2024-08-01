from typing import Optional, List

from ghostiss.abc import Identifier
from ghostiss.core.ghosts.thoughts import Mindset, Thought
from ghostiss.entity import EntityMeta
from ghostiss.core.moss.exports import Exporter


class FakeMindset(Mindset):
    def recall(self, description: str, limit: int = 10, offset: int = 0) -> List[Identifier]:
        return [
            Identifier(
                id="",
                name="",
                description="",
            )
        ]

    def remember(self, thought: Thought) -> None:
        return None

    def get_thought(self, thought_id: str) -> Optional[Thought]:
        return None

    def force_get_thought(self, thought_id: str) -> Thought:
        raise NotImplementedError("thought id '{}' not found".format(thought_id))

    def new_entity(self, meta_data: EntityMeta) -> Optional[Thought]:
        return None


EXPORTS = Exporter().attr('mindset', FakeMindset(), Mindset)
