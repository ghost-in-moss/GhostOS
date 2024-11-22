from os.path import join
import argparse
import sys
import os

"""
this script is used to clear the local file cache in runtime directory
"""

__all__ = ['clear_directory']

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

    for root, dirs, files in os.walk(directory):
        for name in files:
            if name not in ignore_patterns:
                file_path = os.path.join(root, name)
                try:
                    os.remove(file_path)
                    cleared_files_count += 1
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")

        if not recursive:
            break
        for dir_path in dirs:
            real_dir_path = os.path.join(root, dir_path)
            clear_directory(real_dir_path, recursive=recursive, depth=depth + 1)
            os.rmdir(real_dir_path)

    return cleared_files_count


def main():
    parser = argparse.ArgumentParser(
        description="clear temp files in runtime directories",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
    )
    parser.add_argument(
        "--threads", "-t",
        action="store_true",
    )
    parser.add_argument(
        "--tasks", "-k",
        action="store_true",
    )
    parser.add_argument(
        "--processes", "-p",
        action="store_true",
    )
    parser.add_argument(
        "--cache", "-c",
        action="store_true",
    )
    parser.add_argument(
        "--prompts", "-m",
        action="store_true",
    )
    parser.add_argument(
        "--logs", "-l",
        action="store_true",
    )
    parser.add_argument(
        "--variables", "-v",
        action="store_true",
    )
    from ghostos.bootstrap import workspace_dir
    runtime_dir = join(workspace_dir, "runtime")
    parsed = parser.parse_args(sys.argv[1:])
    _all = parsed.all
    print(f"Clearing runtime files in {runtime_dir}")
    done = 0
    if _all or parsed.tasks:
        cleared = clear_directory(join(runtime_dir, "tasks"), recursive=True)
        done += 1
        print(f"clear runtime/tasks files: {cleared}")
    if _all or parsed.processes:
        cleared = clear_directory(join(runtime_dir, "processes"), recursive=True)
        done += 1
        print(f"clear runtime/processes files: {cleared}")
    if _all or parsed.threads:
        cleared = clear_directory(join(runtime_dir, "threads"), recursive=True)
        done += 1
        print(f"clear runtime/threads files: {cleared}")
    if _all or parsed.cache:
        cleared = clear_directory(join(runtime_dir, "cache"), recursive=True)
        done += 1
        print(f"clear runtime/cache files: {cleared}")
    if _all or parsed.prompts:
        cleared = clear_directory(join(runtime_dir, "prompts"), recursive=True)
        done += 1
        print(f"clear runtime/prompts files: {cleared}")
    if _all or parsed.variables:
        cleared = clear_directory(join(runtime_dir, "variables"), recursive=True)
        done += 1
        print(f"clear runtime/prompts files: {cleared}")
    if _all or parsed.logs:
        cleared = clear_directory(join(runtime_dir, "logs"), recursive=True)
        done += 1
        print(f"clear runtime/logs files: {cleared}")

    if not done:
        print(f"no files cleared. please check arguments by '-h' option")


# if __name__ == '__main__':
#     from ghostos.prototypes.console import new_console_app
#     from ghostos.thoughts import new_file_editor_thought
#
#     app = new_console_app(__file__, 2)
#     app.run_thought(
#         new_file_editor_thought(filepath=__file__),
#         instruction="help me to implement clear_directory function."
#     )

if __name__ == "__main__":
    main()
