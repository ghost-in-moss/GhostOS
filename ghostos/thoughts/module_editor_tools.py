from typing import Optional
from ghostos.core.ghosts import Operator
from ghostos.core.moss import Moss as Parent
from ghostos.libraries.py_editor import ModuleEditor


# todo: import necessary libraries and methods


class Moss(Parent):
    """
    Moss that equipped with ModuleEditor
    """
    editor: ModuleEditor
    """ the editor about target module """


if __name__ == "__example__":
    def example_append_code_main(moss: Moss) -> Optional[Operator]:
        """
        this example is about user asking to import os library
        """
        # add code to line 2 of target module.
        moss.editor.insert("import os", line_num=2)
        # return none means if print anything, observe them and think again. otherwise do default action awaits.
        return None
