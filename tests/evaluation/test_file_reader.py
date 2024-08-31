import os
from unittest.mock import patch
from evaluation.swe_bench_lite.tools.file_reader import FileReader

def setup_file_reader():
    # Change the directory to the root of the project
    current_dir = os.getcwd()
    project_name = "GhostOS"  # 确保这是你的项目根目录名称
    while os.path.basename(current_dir) != project_name and current_dir != os.path.dirname(current_dir):
        current_dir = os.path.dirname(current_dir)
    os.chdir(current_dir)
    print(f"Changed directory to: {os.getcwd()}")  # Debug print

def test_file_reader():
    setup_file_reader()
    with patch('evaluation.swe_bench_lite.tools.file_reader.FileReader', FileReader):
        file_path = 'tests/evaluation/mock_code.py'  # Updated file path
        print(f"Testing file path: {file_path}")  # Debug print
        print(f"Current working directory: {os.getcwd()}")  # Debug print
        ret = FileReader.read_file(file_path, 1, 500)
        print(ret)
        assert "Showing page 1/1" in ret
        assert "00|class MockClass:" in ret  # Updated expected content
        assert "01|    def __init__(self):" in ret  # Updated expected content
        assert "02|        self.value = 42" in ret  # Updated expected content
        # Add more assertions as needed for the content of mock_code.py

def test_invalid_file_path():
    setup_file_reader()
    with patch('evaluation.swe_bench_lite.tools.file_reader.FileReader', FileReader):
        file_path = 'invalid/file/path.py'
        print(f"Testing invalid file path: {file_path}")  # Debug print
        print(f"Current working directory: {os.getcwd()}")  # Debug print
        ret = FileReader.read_file(file_path, 1, 500)
        assert ret == "It's not a valid file path"

if __name__ == "__main__":
    test_file_reader()
    test_invalid_file_path()
    print("All tests passed!")
