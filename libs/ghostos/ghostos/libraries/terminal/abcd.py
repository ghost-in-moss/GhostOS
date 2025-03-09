import locale
from abc import ABC, abstractmethod
from typing import NamedTuple, List
from datetime import datetime


class Terminal(ABC):
    """
    Abstract base class representing a system terminal interface.
    Provides basic command execution capabilities for OS interactions.
    """

    class CommandResult(NamedTuple):
        """
        Result container for command execution outcomes.
        Attributes:
            exit_code: Process exit code (0 for success)
            stdout: Standard output content
            stderr: Error output content
        """
        exit_code: int
        stdout: str
        stderr: str

    @abstractmethod
    def exec(self, *commands: str, timeout: float = 10.0) -> CommandResult:
        """
        Execute a shell command and return structured results.

        Args:
            commands: Command lines to execute. each command is a full line command.
            (Note: Implementation should handle proper shell escaping)
            timeout: Timeout in seconds

        Returns:
            CommandResult containing exit code and output streams

        Raises:
            RuntimeError: If command execution fails fundamentally
            TimeoutError: If execution exceeds permitted time
        """
        pass


class TerminalContext:
    """
    Environmental context generator for terminal operations.
    Provides system metadata to help language models understand execution context.
    """

    def pwd(self) -> str:
        """Get current working directory with symlink resolution"""
        import os
        return os.getcwd()

    def system_info(self) -> str:
        """Get detailed Ubuntu version information"""
        import platform
        return platform.platform(terse=True)

    def whoami(self) -> str:
        import getpass
        return getpass.getuser()

    def time_context(self) -> datetime:
        """Get precise time with timezone awareness"""
        # todo: 带时区.
        return datetime.now()

    def generate_prompt(self) -> str:
        """
        Compile environmental context into natural language prompt.
        """
        time_context = self.time_context()
        lang, encoding = locale.getdefaultlocale()
        return (
            "[System Context]\n"
            f"OS: {self.system_info()}\n"
            f"User: {self.whoami()}\n"
            f"Pwd: {self.pwd()}\n"
            f"TimeZone: {time_context.astimezone().tzinfo}\n"
            f"Time: {time_context.isoformat(' ', 'seconds')}\n"
            f"System Lang: {lang}\n"
            f"System Encoding: {encoding}\n"
        )
