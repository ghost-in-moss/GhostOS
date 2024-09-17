from typing import Optional
from ghostos.core.ghosts import Operator, Replier
from ghostos.core.moss import Moss as Parent
from ghostos.libraries.py_editor import ModuleEditor


class Moss(Parent):
    """
    Moss that equipped with ModuleEditor
    """
    editor: ModuleEditor
    """ the editor about target module """

    replier: Replier
    """ with replier you can send reply in main function"""


if __name__ == "__example__":
    def example_append_code_at_main(moss: Moss) -> Optional[Operator]:
        """
        this example is about you need to add codes to the target module.
        """
        # write the target code as string variable
        code = """
def plus(a, b):
    return a + b
"""
        # using editor api to add code
        moss.editor.append(code)
        # return none means if print anything, observe them and think again. otherwise do default action awaits.
        # NEVER CONFUSE the MOSS interface and the target module.
        # 1. MOSS interface providing you with a python interface to using many libraries, instead of JSON Schema tools.
        # 2. Target module is what you want to handle.
        return None
