from typing import Dict, ClassVar, List, Union

from typing_extensions import Self
import pathlib

from ghostos import Operator, Session
from ghostos.libraries.project.abcd import Directory, File, PyDevCtx
from ghostos.libraries.project.dev_context import PyDevCtxData
from ghostos.contracts.configs import YamlConfig
from ghostos.core.messages import MessageType, Role
from ghostos_common.helpers import generate_directory_tree, yaml_pretty_dump, get_module_fullname_from_path
from ghostos_common.helpers.files import DescriptionsGetter
from ghostos_moss import moss_runtime_ctx
from pydantic import Field
from contextlib import contextmanager
import time


class DirectoryData(YamlConfig):
    relative_path = ".ghostos_dir.yml"

    dev_contexts: Dict[str, PyDevCtxData] = Field(
        default_factory=dict,
        description="the saved dev context from title to value",
    )
    file_desc: Dict[str, str] = Field(
        default_factory=lambda: {".": ""},
    )
    editing: Union[str, None] = Field(
        default=None,
        description="the editing filename relative to the current directory",
    )
    updated: int = Field(
        default=0,
        description="the updated timestamp",
    )

    def save_to(self, path: pathlib.Path) -> None:
        if not path.is_dir():
            raise NotADirectoryError(f'{path} is not a directory')
        now = int(time.time())
        self.updated = now
        content = yaml_pretty_dump(self.model_dump(exclude_defaults=True))
        file = path.joinpath(self.relative_path)
        with open(file, "w") as f:
            f.write(content)

    def get_description(self, key=".") -> str:
        return self.file_desc.get(key, "")

    def set_description(self, key=".", desc: str = "") -> None:
        self.file_desc[key] = desc

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

    def set_dev_context(self, data: PyDevCtxData, name: str = ".") -> None:
        self.dev_contexts[name] = data


class DirectoryFileDescriptionGetter(DescriptionsGetter):

    def __init__(self, root: pathlib.Path):
        self.root = root
        self._cached = {}

    def get(self, path: pathlib.Path, default: Union[str, None] = None) -> Union[str, None]:
        real_path = self.root.joinpath(path).absolute()
        if real_path in self._cached:
            return self._cached[real_path]
        value = self._get(real_path, default)
        self._cached[real_path] = value
        return value

    def _get(self, path: pathlib.Path, default: Union[str, None] = None) -> Union[str, None]:
        if path.is_dir():
            return DirectoryData.get_from(path).get_description()
        elif path.is_file():
            return DirectoryData.get_from(path.parent).get_description(path.name)
        return default


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

    def read(self, line_number: bool = True, detail: bool = True) -> str:
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
        if not detail:
            return content

        modulename = get_module_fullname_from_path(str(self.path), use_longest_match=True)
        if modulename is not None:
            py_info = f"\nfile is python module `{modulename}`."
            with moss_runtime_ctx(modulename) as rtm:
                imported_prompt = rtm.prompter().get_imported_attrs_prompt()
                if imported_prompt:
                    py_info += "imported attr information are: \n```python\n" + imported_prompt + "\n```"

            return (f'content of file `{self.path}` are:'
                    f'\n\n<content length="{length}">\n{content}{suffix}\n</content>\n{py_info}')

        return f'<content length="{length}">\n{content}{suffix}\n</content>'

    def is_readable(self):
        allowed = False
        for ext in self.allow_ext:
            if self.path.name.endswith(ext):
                allowed = True
        return allowed

    def write(self, content: str, append: bool = False) -> None:
        if not self.is_readable():
            raise NotImplementedError(f'{self.path} is not writable yet')

        if append:
            origin = str(self.path.read_text())
            content = origin + "\n" + content
        self.path.write_text(content)

    def insert(self, content: str, start: int = -1, end: int = -1) -> None:
        if not self.is_readable():
            raise NotImplementedError(f'{self.path} is not writable yet')

        insert_content(self.path, content, start, end)

    def continuous_write(self, instruction: str, start: int = -1, end: int = 0, max_round: int = 10) -> Operator:
        if not self.is_readable():
            raise NotImplementedError(f'{self.path} is not writable yet')

        return ContinuousWritingFileOperator(
            filepath=self.path,
            instruction=instruction,
            start=start,
            end=end,
            max_round=max_round,
        )


def insert_content(path: pathlib.Path, content: str, start: int, end: int) -> None:
    origin = path.read_text()
    lines = origin.splitlines()
    before = []
    after = []
    while start < 0 < len(lines):
        start = len(lines) + start + 1
    while end < 0 < len(lines):
        end = len(lines) + end + 1

    idx = 0
    for line in lines:
        idx += 1
        if idx <= start:
            before.append(line)
        elif idx >= end and idx > start:
            after.append(line)
    before.extend([content])
    before.extend(after)
    with open(path, "w") as f:
        f.write("\n".join(before))


class ContinuousWritingFileOperator(Operator):

    def __init__(
            self,
            filepath: pathlib.Path,
            instruction: str,
            start: int,
            end: int,
            max_round: int,
            end_token: str = "<end-continuous-writing>",
    ):
        self.filepath = filepath
        self.instruction = instruction
        self.start = start
        self.end = end
        self.contents = []
        self.max_round = max_round
        self.end_token = end_token
        self.filename = self.filepath.name

    def run(self, session: Session) -> Union[Operator, None]:
        llm_api = session.ghost_driver.get_llm_api(session)
        prompt = session.ghost_driver.get_current_prompt(session)
        idx = 0
        added = []
        while idx < self.max_round:
            _prompt = prompt.model_copy(deep=True)
            _prompt.clear_callable()
            _prompt.added.extend(added)
            _prompt.added.append(Role.new_system(self._turn_instruction(idx)))

            items = llm_api.deliver_chat_completion(_prompt, stream=session.allow_streaming())
            messages, callers = session.respond(items)
            has_end_token = False
            for msg in messages:
                if not MessageType.is_text(msg):
                    continue
                if msg.content.endswith(self.end_token):
                    has_end_token = True
                    replaced = msg.content.replace(self.end_token, "")
                    msg.memory = msg.content
                    msg.content = replaced
                    added.append(msg)
                self.contents.append(msg.content)
            if has_end_token:
                break
        # do insert.
        insert_content(self.filepath, "\n".join(self.contents), self.start, self.end)
        return session.mindflow().think(
            Role.new_system(
                f"continuous writing on {self.filename} at {self.start} to {self.end} is done after {idx} round"),
        )

    def _turn_instruction(self, idx: int) -> str:
        return f"""
You are at continuous writing stage, writing text content into file {self.filename} continuously. 
The block you are editing are from the origin content line `{self.start}` to `{self.end}`.
All your generation will directly write into the block, SO DON'T WRITE ANYTHING not about the file. 

And Current round is {idx}/{self.max_round}. 

When you put end tokens `{self.end_token}` at end of your output, means all your output is done, and the loop will be break.
The end tokens will not record to the block you are editing.
Only use end tokens when you complete the whole writing. 

Follow the instruction: 
```
{self.instruction}
```

now start your writing:
"""

    def destroy(self):
        pass


class DirectoryImpl(Directory):
    default_ignores: ClassVar[List[str]] = [
        ".gitignore",
        DirectoryData.relative_path,
        "__pycache__",
        '.git/',
        '.idea/',
    ]

    def __init__(self, path: pathlib.Path, ignores: List[str] = None):
        editing_file = None
        if not path.is_dir():
            editing_file = path.name
            path = path.parent
        self.path = path
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
        self.focus(editing_file)

    def get_ignores(self) -> List[str]:
        return self._ignores

    def full_context(self) -> str:
        editing_context = "empty"
        if self.data.editing:
            try:
                file = self.edit(self.data.editing)
                editing_context = file.read(line_number=True, detail=True)
            except Exception as e:
                editing_context = f"can not read content on error {e}"

        return f"""
full context of the Directory instance:

<Directory path=`{self.path}`>

The sub-files and sub-dirs of the current directory are as follows (recursion depth 2).
```
{self.lists(recursion=2)}
```

DevContext at `Directory.ctx` are: 
<dev-context>
{self.ctx.full_context()}
</dev-context>

all the available dev contexts from name (or path) to description are: 
```yaml
{yaml_pretty_dump(self.existing_dev_contexts())}
```
<editing file=`{self.data.editing}`>
```text
{editing_context}
```
</editing>

</Directory>
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
        getter = DirectoryFileDescriptionGetter(self.path)
        return generate_directory_tree(
            self.path,
            prefix=prefix,
            recursion=recursion,
            descriptions=getter,
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

    def mkdir(self, subdir: str, desc: str, dev_ctx: Union[PyDevCtx, None] = None) -> bool:
        real_subdir = self.path.joinpath(subdir).absolute()
        real_subdir.relative_to(self.path)
        if real_subdir.exists():
            return False
        real_subdir.mkdir()
        data = DirectoryData.get_from(real_subdir)
        data.set_description(desc=desc)
        if dev_ctx is not None:
            ctx = PyDevCtxData(**dev_ctx.model_dump())
            data.set_dev_context(ctx)
        return True

    def touch(self, sub_file: str, desc: str, dev_ctx: Union[PyDevCtx, None] = None) -> bool:
        real_sub_path = self.path.joinpath(sub_file).absolute()
        real_sub_path.relative_to(self.path)
        if real_sub_path.exists():
            return False
        real_sub_path.touch()
        data = DirectoryData.get_from(real_sub_path.parent)
        data.set_description(desc=desc, key=real_sub_path.name)
        if dev_ctx is not None:
            ctx = PyDevCtxData(**dev_ctx.model_dump())
            data.set_dev_context(ctx, name=real_sub_path.name)
        return True

    def focus(self, file_path: Union[str, None]) -> Union[File, None]:
        if file_path is None:
            self.data.editing = None
            return None
        file = self.edit(file_path)
        self.data.editing = file_path
        return file

    def edit(self, file_path: str) -> FileImpl:
        real_path = self.path.joinpath(file_path).absolute()
        if not real_path.is_file():
            raise ValueError(f"'{file_path}' is not a file")
        relative_path_obj = real_path.relative_to(self.path)
        relative_path = str(relative_path_obj)
        dev_context = self.data.get_dev_context(relative_path)
        return FileImpl(
            real_path,
            dev_ctx=dev_context,
        )

    def save_dev_contexts(self):
        self.data.save_to(self.path)

    def save_data(self) -> None:
        self.data.save_to(self.path)


if __name__ == "__main__":
    current = pathlib.Path(__file__)
    d = DirectoryImpl(current.parent)
    with d:
        d.focus(current.name)
        print(d.lists())
        print(d.ctx.full_context())
        d.describe("abcd.py", "abstract classes")
        d.save_dev_contexts()

        print("+++++")
        print(d.dev_contexts())

        print("+++++")
        print(d.full_context())

        editing = d.edit(current.name)
        print("+++++++++++ path", editing.path)

        editing.write("hello", append=True)
        insert_content(editing.path, "world", -1, -1)
