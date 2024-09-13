from typing import Optional
from ghostos.framework.ghostos import demo_ghostos
from ghostos.framework.ghosts.demo import DemoGhostConf
from ghostos.prototypes.console.console import ConsolePrototype
from ghostos.core.ghosts import Thought
from ghostos.helpers import get_calling_modulename, import_from_path, md5, uuid
from ghostos.core.moss.decorators import no_prompt

__all__ = [
    'ConsolePrototype',
    'run_demo_console',
    'run_demo_thought',
]

_ran_demo_thought = False


@no_prompt
def run_demo_thought(
        thought: Thought,
        *,
        username: str = "BrightRed",
        ghost_name: str = "Ghost",
        debug: bool = False,
        meta_prompt: str = "",
        long_term_session: bool = False,
):
    global _ran_demo_thought
    if _ran_demo_thought:
        return
    _ran_demo_thought = True
    ghostos = demo_ghostos
    modulename = get_calling_modulename(1)
    module = import_from_path(modulename)
    file = module.__file__
    ghost_id = md5(file)
    ghost_conf = DemoGhostConf(
        id=ghost_id,
        name=ghost_name,
        thought_meta=thought.to_entity_meta(),
        meta_prompt=meta_prompt,
    )
    ghostos.register(ghost_conf)
    if long_term_session:
        session_id = ghost_id
    else:
        session_id = uuid()
    console_impl = ConsolePrototype(
        ghostos=ghostos,
        ghost_id=ghost_id,
        username=username,
        debug=debug,
        session_id=session_id,
    )
    console_impl.run()
    _ran_demo_thought = False


_ran_demo_console = False


@no_prompt
def run_demo_console(
        ghost_id: str,
        *,
        username: str = "BrightRed",
        debug: bool = False,
        session_id: Optional[str] = None,
):
    global _ran_demo_console
    if _ran_demo_console:
        return
    _ran_demo_console = True
    ghostos = demo_ghostos
    console_impl = ConsolePrototype(
        ghostos=ghostos,
        ghost_id=ghost_id,
        username=username,
        debug=debug,
        session_id=session_id,
    )
    console_impl.run()
    _ran_demo_console = False
