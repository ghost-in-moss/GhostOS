from typing import Optional
from ghostos.framework.ghostos import demo_ghostos
from ghostos.framework.ghosts.demo import DemoGhostConf
from ghostos.prototypes.console.console import ConsolePrototype
from ghostos.core.ghosts import Thought
from ghostos.helpers import get_calling_modulename, import_from_path, md5

__all__ = ['ConsolePrototype', 'run_demo_console']


def run_demo_thought(
        thought: Thought,
        *,
        username: str = "BrightRed",
        ghost_name: str = "Ghost",
        debug: bool = False,
        meta_prompt: str = "",
):
    ghostos = demo_ghostos
    modulename = get_calling_modulename(1)
    module = import_from_path(modulename)
    file = module.__file__
    ghost_id = md5(file)
    ghost_conf = DemoGhostConf(
        ghost_id=ghost_id,
        name=ghost_name,
        thought_meta=thought.to_entity_meta(),
        meta_prompt=meta_prompt,
    )
    ghostos.register(ghost_conf)
    console_impl = ConsolePrototype(
        ghostos=ghostos,
        ghost_id=ghost_id,
        username=username,
        debug=debug,
        session_id=ghost_id,
    )
    console_impl.run()


def run_demo_console(
        ghost_id: str,
        *,
        username: str = "BrightRed",
        debug: bool = False,
        session_id: Optional[str] = None,
):
    ghostos = demo_ghostos
    console_impl = ConsolePrototype(
        ghostos=ghostos,
        ghost_id=ghost_id,
        username=username,
        debug=debug,
        session_id=session_id,
    )
    console_impl.run()
