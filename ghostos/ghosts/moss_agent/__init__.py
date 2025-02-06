from ghostos.ghosts.moss_agent.agent import MossAgent, MossAgentDriver


def new_moss_agent(
        modulename: str,
        *,
        name: str = None,
        description: str = None,
        persona: str = None,
        instruction: str = None,
        llm_api: str = "",
) -> MossAgent:
    if persona is None:
        persona = f"""
You are an Agent created from python module file. 
Your goal is helping user to: 
- understand the python code.
- interact with the python code that provided to you. 
"""
    if instruction is None:
        instruction = """
- you are kind, helpful agent.
- you are master of python coding. 
"""
    if name is None:
        name = modulename
    if description is None:
        description = f"default moss agent built from python module `{modulename}`."
    return MossAgent(
        moss_module=modulename,
        persona=persona,
        instruction=instruction,
        name=name,
        description=description,
        llm_api=llm_api,
    )
