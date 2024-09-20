from typing import Optional
from ghostos.core.ghosts import Operator, Replier
from ghostos.core.moss import Moss as Parent
from ghostos.libraries.file_editor import FileEditor


class Moss(Parent):
    """
    Moss that equipped with FileEditor
    """
    editor: FileEditor
    """ the editor managing the current file """

    replier: Replier
    """ with replier you can send reply in main function"""
