from typing import Union, Type
from ghostos.ghosts.moss_ghost.impl import MossGhost, MossGhostDriver, BaseMossGhostMethods
from ghostos_common.helpers import generate_import_path

__all__ = ["MossGhost", "BaseMossGhostMethods", "MossGhostDriver", 'new_moss_ghost']


def new_moss_ghost(
        modulename: str,
        *,
        default_moss_type: Union[str, None, Type] = None,
        name: str = None,
        description: str = None,
        persona: str = None,
        instruction: str = None,
        llm_api: str = "",
        safe_mode: bool = True,
) -> MossGhost:
    if persona is None:
        persona = f"""
You are an Agent created from python module {modulename}. 

Your goal is helping user to: 
- understand the module, explain its functionality.
- interact with the python tools that provided to you. 
- modify the module's code if you are equipped with SelfUpdater. 
"""
    if instruction is None:
        instruction = """
- you are kind, helpful agent.
- you are master of python coding. 
"""
    if name is None:
        name = modulename
        name = name.replace(".", "_")
    if description is None:
        description = f"default moss agent built from python module `{modulename}`."
    if default_moss_type and not isinstance(default_moss_type, str):
        default_moss_type = generate_import_path(default_moss_type)
    return MossGhost(
        name=name,
        module=modulename,
        default_moss_type=default_moss_type,
        description=description,
        persona=persona,
        instruction=instruction,
        llm_api=llm_api,
        safe_mode=safe_mode,
    )
