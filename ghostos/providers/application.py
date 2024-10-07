from typing import List
from ghostos.container import Provider, Contracts
from ghostos.contracts.pool import Pool, DefaultPoolProvider
from ghostos.contracts.shutdown import Shutdown, ShutdownProvider
from ghostos.contracts.modules import Modules, DefaultModulesProvider
from ghostos.core.moss import MossCompiler, DefaultMOSSProvider
from ghostos.framework.storage import Storage, FileStorage, FileStorageProvider
from ghostos.framework.workspaces import Workspace, BasicWorkspaceProvider
from ghostos.framework.configs import Configs, WorkspaceConfigsProvider
from ghostos.framework.processes import WorkspaceProcessesProvider, Processes
from ghostos.framework.threads import Threads, WorkspaceThreadsProvider
from ghostos.framework.tasks import Tasks, WorkspaceTasksProvider
from ghostos.framework.eventbuses import EventBus, MemEventBusImplProvider
from ghostos.framework.llms import LLMs, ConfigBasedLLMsProvider
from ghostos.framework.logger import LoggerItf, NamedLoggerProvider


"""
Application level contracts and providers. 
"""

application_contracts = Contracts([
    # workspace contracts
    Storage,  # workspace root storage
    FileStorage,  # workspace root storage is a file storage
    Workspace,  # application workspace implementation
    Configs,  # application configs repository

    # system contracts
    Pool,  # multi-thread or process pool to submit async tasks
    Shutdown,  # graceful shutdown register
    LLMs,  # LLMs interface
    LoggerItf,  # the logger instance of application
    Modules,  # the import_module proxy

    # moss
    MossCompiler,

    # session contracts
    Processes,  # application processes repository
    Threads,  # application threads repository
    Tasks,  # application tasks repository
    EventBus,  # application session eventbus
])


def default_application_providers(
        root_dir: str,
        logger_name: str,
        workspace_dir: str = "workspace",
        workspace_configs_dir: str = "configs",
        workspace_runtime_dir: str = "runtime",
        runtime_processes_dir: str = "processes",
        runtime_tasks_dir: str = "tasks",
        runtime_threads_dir: str = "threads",
        llms_conf_path: str = "llms_conf.yml",
) -> List[Provider]:
    """
    application default providers that bind contracts to application level container.
    todo: use manager provider to configurate multiple kinds of implementation
    """
    return [
        FileStorageProvider(root_dir),
        BasicWorkspaceProvider(
            workspace_dir=workspace_dir,
            configs_path=workspace_configs_dir,
            runtime_path=workspace_runtime_dir,
        ),
        WorkspaceConfigsProvider(),
        WorkspaceProcessesProvider(runtime_processes_dir),
        WorkspaceTasksProvider(runtime_tasks_dir),
        WorkspaceThreadsProvider(runtime_threads_dir),
        DefaultPoolProvider(100),
        ConfigBasedLLMsProvider(llms_conf_path),
        DefaultModulesProvider(),
        MemEventBusImplProvider(),
        ShutdownProvider(),
        NamedLoggerProvider(logger_name),
        DefaultMOSSProvider(),
    ]
