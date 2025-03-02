from os.path import join
import argparse
import sys
import os

"""
this script is used to clear the local file cache in runtime directory
"""

__all__ = ['clear_directory', 'clear_runtime', 'clear_assets']

ignore_patterns = ['.gitignore']


def clear_directory(directory: str, recursive=True, depth: int = 0) -> int:
    """
    clear all files in directory recursively except the files match any of ignore_patterns
    :param directory: the target directory
    :param recursive: recursively clear all files in directory
    :param depth: the depth of recursion
    :return: number of files cleared
    """

    cleared_files_count = 0

    print("search file at %s" % directory)
    for root, dirs, files in os.walk(directory):
        for name in files:
            if name not in ignore_patterns:
                file_path = os.path.join(root, name)
                try:
                    print(f"- remove file: {file_path}")
                    os.remove(file_path)
                    cleared_files_count += 1
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")

        if not recursive:
            break
        for dir_path in dirs:
            real_dir_path = os.path.join(root, dir_path)
            clear_directory(real_dir_path, recursive=recursive, depth=depth + 1)
            # os.rmdir(real_dir_path)

    return cleared_files_count


def clear_assets(sub_path: str) -> int:
    from ghostos.bootstrap import get_bootstrap_config
    bootstrap_config = get_bootstrap_config()
    asserts_dir = bootstrap_config.abs_assets_dir()

    target_dir = asserts_dir
    if sub_path:
        target_dir = join(target_dir, sub_path)

    cleared = clear_directory(target_dir, recursive=True)
    return cleared


def clear_runtime(sub_path: str) -> int:
    from ghostos.bootstrap import get_bootstrap_config
    bootstrap_config = get_bootstrap_config()
    runtime_dir = bootstrap_config.abs_runtime_dir()

    target_dir = runtime_dir
    if sub_path:
        target_dir = join(target_dir, sub_path)

    cleared = clear_directory(target_dir, recursive=True)
    return cleared


def main():
    parser = argparse.ArgumentParser(
        description="clear temp files in workspace runtime directories",
    )
    parser.add_argument(
        "--path", "-p",
        help="the target directory path, if not given, clear every sub directory in runtime.",
        type=str,
        required=False,
        default=None,
    )
    parsed = parser.parse_args(sys.argv[1:])
    clear_runtime(parsed.path)
