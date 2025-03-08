from ghostos.abcd import Context
from ghostos_common.prompter import DataPOM, DataPOMDriver
from ghostos_container import Container


class ProjectManagerContext(Context, DataPOM):
    pass


class ProjectManagerContextDriver(DataPOMDriver):

    def self_prompt(self, container: Container) -> str:
        pass

    def get_title(self) -> str:
        pass
