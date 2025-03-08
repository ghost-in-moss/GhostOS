import pathlib
from typing import Optional, Union, Iterable
from typing_extensions import Self
from ghostos.ghosts.moss_ghost import MossGhost, MossGhostDriver
from ghostos.ghosts.project_manager import project_manager_moss
from ghostos.core.llms import ModelConf
from pydantic import Field
from ghostos_common.helpers import md5
from ghostos.libraries.terminal import TerminalProvider
from ghostos.libraries.project import ProjectManagerProvider
from pathlib import Path

from ghostos_container import Provider

DEFAULT_INSTRUCTION = """
## **1. Interacting with Engineer Users**
- **Be Clear and Concise**: Use straightforward, technical language that engineers can easily understand.  
- **Provide Context**: Always explain the purpose and outcome of your actions.  
- **Ask for Clarification**: Politely request more details if a user’s request is unclear, or you can not get enough context.
- **Offer Suggestions**: Propose alternatives if a request cannot be fulfilled.  

## **2. Encouraging Proactive Problem Solving**
- **Anticipate Needs**: Suggest related tasks based on the user’s actions.  
- **Highlight Issues**: Notify users of potential problems immediately.  
- **Automate Repetitive Tasks**: Offer to automate frequent or tedious tasks.  

## **3. Security Considerations**
- **Confirm Destructive Actions**: Always ask for confirmation before irreversible actions.  
- **Notify Users of Risks**: Warn users of potential risks before proceeding.  

## **4. Expressing Gratitude**
- **Acknowledge User Input**: Thank users for their instructions and feedback.  
- **Encourage Feedback**: Invite users to share suggestions for improvement, and record important ones on DevContext.

"""

ROOT_INSTRUCTION_FILE = "instructions.md"

ROOT_PERSONA_FILE = "persona.md"

DEFAULT_PERSONA = """
Powered By: GhostOS Project
Capabilities: Expert in project management, powered by advanced AI and the MOSS protocol, 
with full-code interface proficiency in Python tools.
"""


class ProjectManagerGhost(MossGhost):
    """
    Specialist agent to manage any project
    """
    project_root: str = Field(description="project absolute root path or relative path to cwd")
    working_on: Optional[str] = Field(default=None,
                                      description="working on directory or filename relative to project_root")

    @classmethod
    def new(
            cls,
            root_dir: Union[str, pathlib.Path, None],
            working_on: Union[str, None] = None,
            safe_mode: bool = True,
            *,
            name: str = "",
            description: str = "",
            persona: str = "",
            instruction: str = "",
            llm_api: str = "",
            model: Optional[ModelConf] = None,
    ) -> Self:
        if not name:
            name = "GhostOS-Project-Manager"
        if not description:
            description = cls.__doc__
        if root_dir is None:
            root_dir = Path.cwd()

        root_path = pathlib.Path(root_dir).resolve().absolute()
        if not persona:
            root_persona_file = root_path.joinpath(ROOT_PERSONA_FILE)
            if root_persona_file.exists():
                persona = root_persona_file.read_text()
            else:
                persona = DEFAULT_PERSONA
        if not instruction:
            instruction_file = root_path.joinpath(ROOT_INSTRUCTION_FILE)
            if instruction_file.exists():
                instruction = instruction_file.read_text()
            else:
                instruction = DEFAULT_INSTRUCTION
        return cls(
            name=name,
            project_root=str(root_path),
            working_on=working_on,
            module=project_manager_moss.__name__,
            description=description,
            persona=persona,
            instruction=instruction,
            llm_api=llm_api,
            model=model,
            safe_mode=safe_mode,
            id=md5(f"project-manager-{root_path}-{working_on}"),
        )


class ProjectManagerGhostDriver(MossGhostDriver):
    ghost: ProjectManagerGhost

    def providers(self) -> Iterable[Provider]:
        yield from super().providers()

        yield TerminalProvider(self.is_safe_mode())
        yield ProjectManagerProvider(
            self.ghost.project_root,
            self.ghost.working_on,
        )


ProjectManagerGhost.DriverType = ProjectManagerGhostDriver
