from abc import ABC, abstractmethod
from typing import NamedTuple
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
    def exec(self, command: str, timeout: float) -> CommandResult:
        """
        Execute a shell command and return structured results.

        Args:
            command: Command string to execute
            (Note: Implementation should handle proper shell escaping)
            timeout: Timeout in seconds

        Returns:
            CommandResult containing exit code and output streams

        Raises:
            RuntimeError: If command execution fails fundamentally
            TimeoutError: If execution exceeds permitted time
        """
        pass


class TerminalContext(ABC):
    """
    Environmental context generator for terminal operations.
    Provides system metadata to help language models understand execution context.
    """

    @abstractmethod
    def pwd(self) -> str:
        """
        Get current working directory path.
        Returns:
            Absolute path string representing current location
        """
        pass

    @abstractmethod
    def os_type(self) -> str:
        """
        Describe operating system characteristics.
        Returns:
            Natural language description of the OS (e.g. 'Linux', 'Windows 11', 'macOS 13.5')
        """
        pass

    @abstractmethod
    def whoami(self) -> str:
        """
        Identify current user context.
        Returns:
            User information string (format: 'username@hostname [privilege_level]')
        """
        pass

    @abstractmethod
    def system_architecture(self) -> str:
        """
        Detect hardware architecture.
        Returns:
            Architecture description (e.g. 'x86_64', 'arm64')
        """
        pass

    @abstractmethod
    def time_context(self) -> datetime:
        """
        Get current system time.
        Returns:
            Timezone-aware datetime object
        """
        pass

    def generate_prompt(self) -> str:
        """
        Compile environmental context into natural language prompt.

        Default implementation structure:
        [System Context]
        OS: {os_type}
        User: {whoami}
        Directory: {pwd}
        Time: {time_context}
        Architecture: {system_architecture}
        Path: {executable_path}
        """
        return (
            "[System Context]\n"
            f"OS: {self.os_type()}\n"
            f"User: {self.whoami()}\n"
            f"Directory: {self.pwd()}\n"
            f"Time: {self.time_context().isoformat(sep=' ', timespec='seconds')}\n"
            f"Architecture: {self.system_architecture()}\n"
        )
