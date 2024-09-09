import os
import math
from ghostos.core.moss.decorators import cls_definition


@cls_definition()
class FileReader:
    """
    Must use this when you want to read source file in file system
    """
    max_line_of_file = 20000

    @staticmethod
    def __get_digit_size(number: int) -> int:
        ret = 0
        while number >= 1:
            number /= 10
            ret += 1
        return ret

    @staticmethod
    def read_file(path, page_number=1, page_size=500) -> str:
        """
        page_number is from 1 to n
        """
        abs_path = os.path.abspath(path)
        print(f"Current working directory: {os.getcwd()}")  # Debug print
        print(f"Checking file path: {path}")  # Debug print
        print(f"Absolute file path: {abs_path}")  # Debug print
        is_valid_file_path = os.path.exists(abs_path) and os.path.isfile(abs_path)
        if not is_valid_file_path:
            print(f"Path exists: {os.path.exists(abs_path)}")  # Debug print
            print(f"Is file: {os.path.isfile(abs_path)}")  # Debug print

            return "It's not a valid file path"

        with open(abs_path, "r") as f:
            lines = f.readlines()

            if len(lines) > FileReader.max_line_of_file:
                return f"The number of line {len(lines)} exceeded our limit: {FileReader.max_line_of_file}"

            digit_size = FileReader.__get_digit_size(len(lines))

            page_numbers = math.ceil(len(lines) / page_size)
            if page_numbers < page_number:
                return f"page_number: {page_number} outbound the max page number ({page_numbers}) of this file "
            output_lines = []
            for i in range((page_number - 1) * page_size, min(page_number * page_size, len(lines))):
                output_lines.append(f'{i:0{digit_size}}|' + lines[i].rstrip())

            last_sentence = f"[Showing page {page_number}/{page_numbers} , specify the page_number to see more content in this file]"
            output_lines.append(last_sentence)

            return '\n'.join(output_lines)
