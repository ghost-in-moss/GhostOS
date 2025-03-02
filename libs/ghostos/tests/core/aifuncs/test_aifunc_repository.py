from ghostos.core.aifunc import AIFuncRepoByConfigsProvider, AIFuncRepository, AIFuncsConf
from ghostos.framework.configs import Configs, MemoryConfigs
from ghostos.contracts.modules import Modules, DefaultModules
from ghostos.contracts.workspace import Workspace
from ghostos.framework.workspaces import BasicWorkspace
from ghostos.framework.storage import MemStorage
from ghostos_container import Container
from ghostos.demo import aifuncs_demo


def test_aifunc_repository():
    container = Container()
    container.set(Modules, DefaultModules())
    container.set(Workspace, BasicWorkspace(MemStorage()))
    container.set(Configs, MemoryConfigs({
        AIFuncsConf.conf_path(): "{}",

    }))
    container.register(AIFuncRepoByConfigsProvider())
    container.bootstrap()

    repo = container.force_fetch(AIFuncRepository)
    result = repo.scan(str(aifuncs_demo.__name__), recursive=True, save=False)
    assert len(result) > 1


