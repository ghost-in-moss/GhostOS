from typing import Dict, ClassVar, List, Union

from typing_extensions import Self
import pathlib

from ghostos.libraries.project.abcd import Directory, File, PyDevCtx
from ghostos.libraries.project.dev_context import PyDevCtxData
from ghostos.contracts.configs import YamlConfig
from ghostos_common.helpers import generate_directory_tree, yaml_pretty_dump, get_module_fullname_from_path
from ghostos_moss import moss_runtime_ctx
from pydantic import Field


class DirectoryData(YamlConfig):
    relative_path = ".ghostos_dir.yml"

    dev_contexts: Dict[str, PyDevCtxData] = Field(
        default_factory=dict,
        description="the saved dev context from title to value",
    )
    file_desc: Dict[str, str] = Field(
        default_factory=dict,
    )

    def save_to(self, path: pathlib.Path) -> None:
        if not path.is_dir():
            raise NotADirectoryError(f'{path} is not a directory')
        content = yaml_pretty_dump(self.model_dump(exclude_defaults=True))
        file = path.joinpath(self.relative_path)
        with open(file, "w") as f:
            f.write(content)

    @classmethod
    def get_from(cls, path: pathlib.Path) -> "DirectoryData":
        if not path.is_dir():
            raise NotADirectoryError(f'{path} is not a directory')
        file = path.joinpath(cls.relative_path)
        if not file.exists():
            return cls()
        with open(file, "r") as f:
            content = f.read()
            return cls.unmarshal(content)

    def get_dev_context(self, name: str) -> PyDevCtxData:
        if name in self.dev_contexts:
            return self.dev_contexts[name]
        data = PyDevCtxData(title=name)
        self.dev_contexts[name] = data
        return data


class FileImpl(File):
    allow_ext: ClassVar[List[str]] = [
        ".md", ".txt", ".py", ".ipynb", ".ts", ".php", ".html", ".js", ".css", ".yaml",
        ".yml", ".toml", ".json"
    ]

    def __init__(
            self,
            filepath: pathlib.Path,
            dev_ctx: PyDevCtxData,
    ):
        if filepath.is_dir():
            raise TypeError(f"{filepath} is not a directory")
        self.path = filepath
        self.ctx = dev_ctx
        self.max_read_size = 5000

    def read(self, line_number: bool = True) -> str:
        allowed = self.is_readable()
        for ext in self.allow_ext:
            if self.path.name.endswith(ext):
                allowed = True
        if not allowed:
            return f"File {self.path.name} are not readable now"

        content = self.path.read_text()
        length = len(content)
        suffix = ""
        if length > self.max_read_size:
            content = content[:self.max_read_size]
            suffix = "..."
        if line_number:
            lines = content.splitlines()
            updated = []
            idx = 0
            for line in lines:
                idx += 1
                updated.append(f"{idx}|{line}")
            content = "\n".join(updated)

        modulename = get_module_fullname_from_path(str(self.path), use_longest_match=True)
        py_info = ""
        if modulename is None:
            py_info = f"\n\nfile is also python module `{modulename}`."
            # add moss imported attrs reflection
            with moss_runtime_ctx(modulename) as runtime:
                imported_prompt = runtime.prompter().get_imported_attrs_prompt()
                if imported_prompt is None:
                    py_info += f"\n<imported_attr_info>\n{imported_prompt}\n</imported_attr_info>"

        return f'<content length="{length}">{content}{suffix}</content>{py_info}'

    def is_readable(self):
        allowed = False
        for ext in self.allow_ext:
            if self.path.name.endswith(ext):
                allowed = True
        return allowed

    def write(self, content: str, append: bool = False) -> None:
        if not self.is_readable():
            raise NotImplementedError(f'{self.path} is not writable yet')

        content = str(self.path.read_text())
        if append:
            content += "\n" + content
        with open(self.path, "w") as f:
            f.write(content)

    def insert(self, content: str, start: int, end: int) -> None:
        origin = self.path.read_text()
        lines = origin.splitlines()
        before = []
        after = []
        idx = 0
        for line in lines:
            idx += 1
            if idx < start:
                before.append(line)
            elif idx >= end:
                after.append(line)
        before.extend([content])
        before.extend(after)
        with open(self.path, "w") as f:
            f.writelines(before)


class DirectoryImpl(Directory):
    default_ignores: ClassVar[List[str]] = [
        ".gitignore",
        DirectoryData.relative_path,
        "__pycache__",
    ]

    def __init__(self, path: pathlib.Path, ignores: List[str] = None, relative: Union[str, None] = None):
        self.path = path
        if relative is None:
            relative = self.path.absolute()
        self.relative = relative
        self.data = DirectoryData.get_from(path)
        self.ctx = self.data.get_dev_context('.')
        if not self.ctx.desc:
            self.ctx.desc = "dev context of this directory"
        if ignores is None:
            ignores = self.default_ignores.copy()
        gitignore = path.joinpath(".gitignore")
        if gitignore.exists():
            with open(gitignore, "r") as f:
                content = f.read()
                ignores.extend(content.splitlines())
        self._ignores = []
        for ignore in ignores:
            ignore = ignore.strip()
            if ignore.startswith('#'):
                continue
            self._ignores.append(ignore)

    def full_context(self) -> str:
        return f"""
full context of the Directory instance on `{self.relative}`:

<Context>

The sub-files and sub-dirs of the current directory are as follows (recursion depth 1).
```
{self.lists(recursion=1)}
```

DevContext at `Directory.ctx` are: 
<dev-context>
{self.ctx.full_context()}
</dev-context>

all the dev contexts from name to description are: 
```yaml
{yaml_pretty_dump(self.existing_dev_contexts())}
```

</Context>
"""

    def dev_contexts(self) -> Dict[str, PyDevCtx]:
        return self.data.dev_contexts

    def existing_dev_contexts(self) -> Dict[str, str]:
        return {ctx.title: ctx.desc for ctx in self.data.dev_contexts.values()}

    def new_dev_context(self, title: str, desc: str) -> PyDevCtxData:
        ctx = PyDevCtxData(title=title, desc=desc)
        self.data.dev_contexts[title] = ctx
        return ctx

    def lists(self, *, prefix: str = "", recursion: int = 0, files: bool = True, dirs: bool = True) -> str:
        return generate_directory_tree(
            self.path,
            prefix=prefix,
            recursion=recursion,
            descriptions=self.data.file_desc,
            ignores=self._ignores,
            files=files,
            dirs=dirs,
        )

    def subdir(self, path: str) -> Self:
        real_path = self.path.joinpath(path)
        try:
            real_path.relative_to(self.path)
        except ValueError:
            raise ValueError(f"'{path}' is not a sub directory")
        if not real_path.is_dir():
            raise ValueError(f"'{path}' is not a directory")
        if not real_path.exists():
            raise ValueError(f"'{path}' does not exist")
        return DirectoryImpl(real_path, self._ignores)

    def describe(self, path: str, desc: str) -> None:
        self.data.file_desc[path] = desc

    def save_dev_contexts(self):
        self.data.save_to(self.path)


if __name__ == "__main__":
    d = DirectoryImpl(pathlib.Path(__file__).parent)
    print(d.lists())
    print(d.ctx.full_context())
    d.describe("abcd.py", "abstract classes")
    d.save_dev_contexts()

    print("+++++")
    print(d.dev_contexts())

    print("+++++")
    print(d.full_context())
