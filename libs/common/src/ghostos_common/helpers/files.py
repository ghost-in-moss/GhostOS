import pathlib
from typing import List, Tuple, Iterable, Dict, Union
import fnmatch

__all__ = ['list_dir', 'is_pathname_ignored', 'generate_directory_tree']


def list_dir(
        current: Union[pathlib.Path, str],
        recursion: int = -1,
        *,
        prefix: str = "",
        ignores: List[str] = None,
        includes: List[str] = None,
        files: bool = True,
        dirs: bool = True,
        depth: int = 0,
) -> Iterable[Tuple[pathlib.Path, int]]:
    """
    List sub filenames and directories.

    :param current: Current path.
    :param prefix: The relative path that starts the listing.
    :param recursion: The recursion depth, 0 means only list current directory. < 0 means not list any.
    :param ignores: The list of ignored path patterns (.gitignore pattern).
    :param includes: if not None, only match include pattern is not ignored
    :param files: True => list files.
    :param dirs: True => list dirs.
    :param depth: current depth
    :return: (path, depth)
    """
    if isinstance(current, str):
        current = pathlib.Path(current)
    # 0. 判断 current 是否为目录, 否则应该抛出异常.
    if not current.is_dir():
        raise ValueError(f"{current} is not a directory")

    # 1. 根据 ignores 参数, 创建一个用于筛选文件的 pattern 集合.
    if ignores is None:
        ignores = []

    # 2. 根据 prefix, 先前进到指定子目录. 不存在也要抛异常.
    target_dir = current / prefix
    if not target_dir.exists():
        raise ValueError(f"Prefix path {prefix} does not exist in {current}")

    # 3. 遍历目标目录
    for path in target_dir.iterdir():
        # 检查路径是否被忽略
        if is_pathname_ignored(path.name, ignores, path.is_dir()):
            continue

        if includes and not is_pathname_ignored(path.name, includes):
            continue

        # 如果是文件且 files=True，则返回
        if path.is_file() and files:
            yield path, depth

        # 如果是目录且 dirs=True，则返回并递归
        if path.is_dir() and dirs:
            yield path, depth
            if recursion != 0:  # 如果 depth == 0，则不递归
                yield from list_dir(
                    path, recursion - 1, prefix="", depth=depth + 1, ignores=ignores, files=files, dirs=dirs
                )


def is_pathname_ignored(path: Union[pathlib.Path, str], pattern: Iterable[str], is_dir: bool) -> bool:
    if not pattern:
        return False
    if isinstance(path, pathlib.Path):
        name = path.name
    else:
        name = str(path)
    for pattern in pattern:
        matched = True
        if pattern.startswith('!'):
            matched = False
            pattern = pattern[1:]
        if is_dir and pattern.endswith('/'):
            pattern = pattern[:-1]
        if fnmatch.fnmatch(name, pattern):
            return matched
    return False


def generate_directory_tree(
        current: Union[pathlib.Path, str],
        recursion: int = -1,
        descriptions: Dict[str, str] = None,
        *,
        prefix: str = "",
        ignores: List[str] = None,
        includes: List[str] = None,
        files: bool = True,
        dirs: bool = True,
        depth: int = 0,
        indent: str = " " * 4
) -> str:
    """
    Generate a text-based directory tree.

    :param current: Current path.
    :param prefix: The relative path that starts the listing.
    :param descriptions: A dictionary of descriptions.
    :param recursion: The recursion depth, 0 means only list current directory. < 0 means not list any.
    :param ignores: The list of ignored path patterns (.gitignore pattern).
    :param includes: if not None, only match include pattern is not ignored
    :param files: True => list files.
    :param dirs: True => list dirs.
    :param depth: current depth
    :param indent: The indentation string for each level of the tree.
    :return: A string representing the directory tree.
    """
    tree = []
    if descriptions is None:
        descriptions = {}

    for path, current_depth in list_dir(current, recursion, prefix=prefix, ignores=ignores, includes=includes,
                                        files=files,
                                        dirs=dirs, depth=depth):
        # Calculate the indentation based on the current depth
        current_indent = indent * current_depth

        desc = ""
        if descriptions:
            relative = path.relative_to(current)
            relative_path = str(relative)
            if relative_path in descriptions:
                got = descriptions.get(relative_path, "")
                got.strip()
                got = got.replace("\n", " ")
                if len(got) > 150:
                    got = got[:150] + "..."
                if got:
                    desc = f" : `{got}`"

        if path.is_dir():
            tree.append(f"{current_indent}📁 {path.name}{desc}")
        else:
            tree.append(f"{current_indent}📄 {path.name}{desc}")

    return "\n".join(tree)
