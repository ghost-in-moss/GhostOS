from typing import Optional
from ghostos.core.ghosts import Operator, Replier
from ghostos.core.moss import Moss as Parent
from ghostos.libraries.file_editor import FileEditor, DirectoryEditor


class Moss(Parent):
    """
    Moss that equipped with DirectoryEditor
    """
    dir_editor: DirectoryEditor
    """ the editor managing the current file """


if __name__ == '__test__':
    """
    define some test code to directly test the current file
    and the tests are good way to prompt LLM in-context learning
    """


    def test_list_only_files(moss: Moss) -> Optional[Operator]:
        """
        this case shows how to use list method of dir_editor and test it
        """
        files = moss.dir_editor.list(depth=0, list_file=True, list_dir=False, formated=False, absolute=False)

        assert "dir_editor_moss_code.py" in files, files
        print(files)  # print values will be buffed by moss
        return None


    __moss_test_cases__ = ['test_list_only_files']
    """use this magic attribute to define test cases for moss test suite"""
