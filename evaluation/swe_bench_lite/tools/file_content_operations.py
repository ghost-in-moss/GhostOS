import os
import math
import logging
from typing import List
from ghostos.core.moss.decorators import cls_outline


@cls_outline()
class FileContentOperations:
    """
    Must use this class when you want to read/find/write file in file system
    """
    max_line_of_file = 20000

    def __init__(self, workspace_root: str):
        """
        :param workspace_root: the root path of the workspace, all operations will be restricted within this root
        """
        self.workspace_root = workspace_root

    def is_path_within_workspace(self, abs_file_path: str) -> bool:
        """
        Check if the given absolute file path is within the workspace root.
        """
        ret = abs_file_path.startswith(self.workspace_root)
        if not ret:
            logging.warning(f"#FileContentOperations: The given absolute file path is not within the workspace root: {abs_file_path}")
        return ret
        
    @staticmethod
    def __get_digit_size(number: int) -> int:
        ret = 0
        while number >= 1:
            number /= 10
            ret += 1
        return ret

    def read_file(self, abs_path, page_number=1, page_size=500) -> str:
        """
        Read the file content with page number and page size(page_number is from 1 to n)
        """

        if not self.is_path_within_workspace(abs_path):
            return f"It must be a valid file path within the workspace: {self.workspace_root}"

        is_valid_file_path = os.path.exists(abs_path) and os.path.isfile(abs_path)
        if not is_valid_file_path:
            print(f"Path exists: {os.path.exists(abs_path)}")  # Debug print
            print(f"Is file: {os.path.isfile(abs_path)}")  # Debug print

            return "It's not a valid file path"

        with open(abs_path, "r") as f:
            lines = f.readlines()

            if len(lines) > FileContentOperations.max_line_of_file:
                return f"The number of line {len(lines)} exceeded our limit: {FileContentOperations.max_line_of_file}"

            digit_size = FileContentOperations.__get_digit_size(len(lines))

            page_numbers = math.ceil(len(lines) / page_size)
            if page_numbers < page_number:
                return f"page_number: {page_number} outbound the max page number ({page_numbers}) of this file "
            output_lines = []
            for i in range((page_number - 1) * page_size, min(page_number * page_size, len(lines))):
                output_lines.append(f'{i:0{digit_size}}|' + lines[i].rstrip())

            last_sentence = f"[Showing page {page_number}/{page_numbers} , specify the page_number to see more content in this file]"
            output_lines.append(last_sentence)

            return '\n'.join(output_lines)
    
    def write_file(self, abs_path: str, content: str) -> str:
        if not self.is_path_within_workspace(abs_path):
            return f"It must be a valid file path within the workspace: {self.workspace_root}"

        with open(abs_path, "w") as f:
            f.write(content)

        return ""


    def find_line_numbers_containing_string(self, abs_filepath: str, search_string: str) -> List[int]:
        """
        Find the line numbers of the specific string in the file
        """
        if not self.is_path_within_workspace(abs_filepath):
            return []

        with open(abs_filepath, 'r') as file:
            lines = file.readlines()
            return [i + 1 for i, line in enumerate(lines) if search_string in line]
        
    def find_files_containing_string_in_directory(self, directory: str, search_string: str) -> List[str]:
        """
        Find the file paths that contain the specific string in the directory
        """
        if not self.is_path_within_workspace(directory):
            return []

        file_paths = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                abs_filepath = os.path.join(root, file)
                if self.is_text_file(abs_filepath):
                    try:
                        with open(abs_filepath, 'r', encoding='utf-8') as f:
                            if search_string in f.read():
                                file_paths.append(abs_filepath)
                    except UnicodeDecodeError:
                        # Skip files that can't be decoded with UTF-8
                        continue
        
        return file_paths

    def is_text_file(self, filepath: str) -> bool:
        """
        Check if a file is likely to be a text file based on its content and extension
        """
        # Check file extension first
        text_extensions = {'.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.yml', '.yaml', '.md',
                           '.go', '.java', '.c', '.cpp', '.h', '.hpp', '.rs', '.rb', '.php', '.ts',
                           '.scala', '.kt', '.swift', '.m', '.sh', '.bat', '.ps1', '.sql', '.r', '.pl',
                           '.cfg', '.ini', '.conf', '.toml', '.rst', '.tex', '.log', '.gitignore',
                           '.env', '.properties', '.gradle', '.pom', '.sbt', '.dockerfile', '.makefile'}
        
        if os.path.splitext(filepath)[1].lower() in text_extensions:
            return True

        # Check if the file is a markdown or restructured text file without extension
        if os.path.basename(filepath).lower() in {'readme', 'license', 'authors', 'contributing'}:
            return True

        try:
            with open(filepath, 'rb') as f:
                return not self.is_binary_string(f.read(1024))
        except IOError:
            return False

    def is_binary_string(self, bytes_to_check: bytes) -> bool:
        """
        Check if a byte string is likely to be binary
        """
        textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
        return bool(bytes_to_check.translate(None, textchars))
