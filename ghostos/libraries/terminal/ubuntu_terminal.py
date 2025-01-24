from typing import Optional

from ghostos.container import Container, INSTANCE
from ghostos.libraries.terminal.abcd import Terminal
from ghostos.libraries.terminal.terminal_impl import SystemTerminal
from ghostos.libraries.terminal.ubuntu_context import UbuntuContext
from ghostos.prompter import Prompter
from ghostos.container import Container, Provider

__all__ = [
    'UbuntuTerminal', 'UbuntuTerminalProvider',
]


class UbuntuTerminal(Terminal, Prompter):

    def __init__(self, safe_mode: bool):
        self._terminal = SystemTerminal(safe_mode=safe_mode)
        self._context = UbuntuContext(self._terminal)

    def exec(self, command: str, timeout: float) -> Terminal.CommandResult:
        return self._terminal.exec(command, timeout)

    def self_prompt(self, container: Container) -> str:
        context_prompt = self._context.generate_prompt()
        return f"""
basic information about the current terminal: 
```bash
{context_prompt}
```
"""

    def get_title(self) -> str:
        return "Ubuntu Terminal"


class UbuntuTerminalProvider(Provider[Terminal]):

    def __init__(self, safe_mode: bool):
        self.safe_mode = safe_mode

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[INSTANCE]:
        return UbuntuTerminal(self.safe_mode)
