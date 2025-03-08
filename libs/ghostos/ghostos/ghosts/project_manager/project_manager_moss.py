from ghostos.abcd import Mindflow
from ghostos_moss import Moss as Parent
from ghostos.libraries.project import ProjectExports
from ghostos.libraries.terminal import Terminal


class Moss(Parent):
    """
    the interfaces for project manager.
    """

    project: ProjectExports.ProjectManager
    """ understand the project files/modules"""

    mindflow: Mindflow
    """ operate your mindflow state"""

    terminal: Terminal
    """interact with terminal"""
