import os
import logging
from typing import List
from ghostos.core.moss.decorators import cls_outline


@cls_outline()
class DirectoryExplorer:
    """
    Must use this class when you want to explore directory in file system
    """

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
            logging.warning(f"#DirectoryExplorer: The given absolute file path is not within the workspace root: {abs_file_path}")
        return ret

    def tree(self, directory, expand_depth=1, max_show_items=10, file_extensions_whitelist=None) -> str:
        """
        Efficient for explore directory structure. More token-efficient than 'tree' or 'os.listdir()'

        :param directory: The target directory path to explore
        :param expand_depth: Controls the depth of directory expansion, -1 means expand all levels
        :param max_show_items: Maximum number of items to display
        :param file_extensions_whitelist: List of file extensions to display, '*' means display all files. directories are always displayed
        :return: A string representation of the directory structure
        """
        if not self.is_path_within_workspace(directory):
            return f"Error: The directory {directory} is not within the workspace."

        result = [f"structure of {directory}:"]
        total_items = [0]

        def tree_inner(directory, expand_depth, indent, max_show_items, file_extensions_whitelist, current_item_count=[0]):
            if not self.is_path_within_workspace(directory):
                return

            if expand_depth == 0 or current_item_count[0] >= max_show_items:
                return

            if file_extensions_whitelist is None:
                file_extensions_whitelist = ['*']

            # Directories to exclude from the output
            exclude_directories = {'.git', '.idea', '__pycache__', '.pytest_cache', '.github', '.gitignore', '.gitattributes',
                                   '.tx', 'LICENSE', 'LICENSE.python', 'AUTHORS', 'CONTRIBUTING.rst'}

            try:
                items = os.listdir(directory)
                items.sort()
            except Exception as e:
                print(f"{indent}Error accessing directory {directory}: {e}")
                return

            # Exclude the directories specified in exclude_directories
            items = [item for item in items if item not in exclude_directories]

            for item in items:
                total_items[0] += 1
                if current_item_count[0] >= max_show_items:
                    continue

                path = os.path.join(directory, item)
                if not self.is_path_within_workspace(path):
                    continue

                if os.path.isdir(path):
                    result.append(f"{indent}{item}/")
                    current_item_count[0] += 1
                    tree_inner(path, expand_depth - 1, indent + "    ", max_show_items, file_extensions_whitelist, current_item_count)
                else:
                    if '*' in file_extensions_whitelist or any(item.endswith(ext) for ext in file_extensions_whitelist):
                        result.append(f"{indent}{item}")
                        current_item_count[0] += 1

        tree_inner(directory, expand_depth, "", max_show_items, file_extensions_whitelist)
        
        if total_items[0] > max_show_items:
            result.append(f"... {total_items[0] - max_show_items} more items")

        return "\n".join(result)

    def list_files_in_dir(self, directory: str) -> List[str]:
        """
        List all files in the specified directory (excluding subdirectories).

        :param directory: Path to the directory to list files from
        :return: List of all files in the directory
        """
        if not self.is_path_within_workspace(directory):
            return []
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) and self.is_path_within_workspace(os.path.join(directory, f))]

    def list_dirs_in_dir(self, directory: str) -> List[str]:
        """
        List all subdirectories in the specified directory.

        :param directory: Path to the directory to list subdirectories from
        :return: List of all subdirectories in the directory
        """
        if not self.is_path_within_workspace(directory):
            return []
        return [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d)) and self.is_path_within_workspace(os.path.join(directory, d))]
