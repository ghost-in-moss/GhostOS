from ghostos.core.moss import moss_test_suite, Execution
from ghostos.libraries.file_editor import DirectoryEditor, DirectoryEditorImpl
from ghostos.demo.src.examples.moss_codes import dir_editor_moss_code
from os.path import dirname

if __name__ == '__main__':
    suite = moss_test_suite()


    def show_test_result(case_name: str, result: Execution):
        """
        callback method for each test case in the target moss module.
        :param case_name: name of the test case
        :param result: the final result from moss_runtime.execute
        """
        print(f"case name: {case_name}:")
        # print the std output during the moss execution.
        print(f"std output during the test:\n{result.std_output}")


    # bind dependencies for test case
    suite.container().set(DirectoryEditor, DirectoryEditorImpl(dirname(__file__)))

    suite.run_module_tests(
        # point the moss file modulename
        modulename=dir_editor_moss_code.__name__,
        # register test callback
        callback=show_test_result,
        # the real modulename that moss compiled
        test_modulename="__test__",
    )