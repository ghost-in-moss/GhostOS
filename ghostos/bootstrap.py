from typing import List, Optional, Tuple
from os.path import dirname, join
from ghostos.abcd import GhostOS
from ghostos.container import Container, Provider, Contracts
from ghostos.prototypes.ghostfunc import init_ghost_func, GhostFunc

import dotenv

# Core Concepts
#
# 1. Ghost and Shell
# We take the word `Ghost` from famous manga movie <Ghost In the Shell> as the abstract of an Agent.
# Ghost shall have concurrent thinking/action capabilities, each thought or task is a fragment of the Ghost mind;
# not like an independent agent in a multi-agent system.
# But you can take `Ghost` as `Agent` for now.
# Also, the word `Shell` in this project refers to the `Body` of the Agent,
# regardless if it is an Embodied Robot/IM chatbot/Website/IDE etc.
#
# 2. MOSS
# stands for "Model-oriented Operating System Simulation".
# - operating system: to operate an Agent's body (Shell), mind, tools.
# - model-oriented: the first class user of the OS is the brain of Ghost(AI models), not Human
# - simulation: we merely use python to simulate the OS, not create a real one.
# Instead of `JSON Schema Tool`, we provide a python code interface for LLMs through MOSS.
# The LLMs can read python context as prompt, then generate python code to do almost everything.
# MOSS can reflect the python module to prompt, and execute the generated python code within a specific python context.
#
# We are aiming to create Fractal Meta-Agent which can generate tools/libraries/Shells/
#
# 3. GhostOS
# Is an agent framework for developers like myself, to define/test/use/modify Model-based Agents.
# Not like MOSS which serve the Models (Large Language Model mostly),
# GhostOS is a framework works for me the Human developer.
#
# 4. Application
# Is the production built with GhostOS.
# There are light-weight applications like `GhostFunc` which is a python function decorator,
# and heavy applications like Streamlit app.
#
# todo: let the gpt4o or moonshot fix my pool english expressions above.


__all__ = [
    'expect_workspace_dir',

    # >>> container
    # GhostOS use IoC Container to manage dependency injections at everywhere.
    # IoCContainer inherit all the bindings from parent Container, and also able to override them.
    # The singletons in the container shall always be thread-safe.
    #
    # The containers nest in multiple levels like a tree:
    # - Application level (global static container that instanced in this file)
    # - GhostOS level (a GhostOS manage as many ghost as it able to)
    # - Ghost level (a Ghost is an instance frame of the Agent's thought)
    # - Moss level (each MossCompiler has it own container)
    # <<<
    'application_container',
    'make_app_container',

    # >>> GhostFunc
    # is a test library, which is able to define dynamic code for an in-complete function.
    # We develop it for early experiments.
    # Check example_ghost_func.py
    # <<<
    'ghost_func',
    'GhostFunc',
    'init_ghost_func',

    # reset ghostos default application instances.
    'reset',
    'reset_at',
    'get_container',

    # default configuration
    'workspace_dir',
    'default_application_contracts',
    'default_application_providers',

    'GHOSTOS_VERSION',
    'get_ghostos',
]

GHOSTOS_VERSION_KEY = "ghostos_version"
GHOSTOS_VERSION = "0.1.0"

# --- prepare application paths --- #


workspace_dir = join(dirname(dirname(__file__)), 'workspace')
"""application root directory path"""


def expect_workspace_dir() -> Tuple[str, bool]:
    from os.path import join, exists, abspath, isdir
    from os import getcwd
    expect_dir = join(getcwd(), "workspace")
    return abspath(expect_dir), exists(expect_dir) and isdir(expect_dir)


# --- default providers --- #


def default_application_contracts() -> Contracts:
    """
    Application level contracts
    """
    from ghostos.core.moss import MossCompiler
    from ghostos.core.messages.openai import OpenAIMessageParser
    from ghostos.contracts.shutdown import Shutdown
    from ghostos.contracts.modules import Modules
    from ghostos.contracts.workspace import Workspace
    from ghostos.contracts.variables import Variables
    from ghostos.framework.configs import Configs
    from ghostos.framework.processes import GoProcesses
    from ghostos.framework.threads import GoThreads
    from ghostos.framework.tasks import GoTasks
    from ghostos.framework.eventbuses import EventBus
    from ghostos.framework.llms import LLMs, PromptStorage
    from ghostos.framework.logger import LoggerItf
    from ghostos.framework.documents import DocumentRegistry
    from ghostos.framework.ghostos import GhostOS
    from ghostos.framework.assets import ImageAssets, AudioAssets
    from ghostos.framework.realtime import Realtime
    from ghostos.core.aifunc import AIFuncExecutor, AIFuncRepository

    return Contracts([
        # workspace contracts
        Workspace,  # application workspace implementation
        Configs,  # application configs repository
        Variables,

        ImageAssets,
        AudioAssets,

        # system contracts
        Shutdown,  # graceful shutdown register
        LLMs,  # LLMs interface
        PromptStorage,

        LoggerItf,  # the logger instance of application
        Modules,  # the import_module proxy

        DocumentRegistry,

        # messages
        OpenAIMessageParser,

        # moss
        MossCompiler,

        # aifunc
        AIFuncExecutor,
        AIFuncRepository,

        # session contracts
        GoProcesses,  # application processes repository
        GoThreads,  # application threads repository
        GoTasks,  # application tasks repository
        EventBus,  # application session eventbus

        # root
        GhostOS,

        Realtime,
    ])


def default_application_providers(
        root_dir: str,
        workspace_configs_dir: str = "configs",
        workspace_runtime_dir: str = "runtime",
        runtime_processes_dir: str = "processes",
        runtime_tasks_dir: str = "tasks",
        runtime_threads_dir: str = "threads",
) -> List[Provider]:
    """
    application default providers
    todo: use manager provider to configurate multiple kinds of implementation
    """
    from ghostos.contracts.shutdown import ShutdownProvider
    from ghostos.contracts.modules import DefaultModulesProvider
    from ghostos.core.moss import DefaultMOSSProvider
    from ghostos.core.messages.openai import DefaultOpenAIParserProvider
    from ghostos.framework.workspaces import BasicWorkspaceProvider
    from ghostos.framework.configs import WorkspaceConfigsProvider
    from ghostos.framework.assets import WorkspaceImageAssetsProvider, WorkspaceAudioAssetsProvider
    from ghostos.framework.processes import WorkspaceProcessesProvider
    from ghostos.framework.threads import MsgThreadsRepoByWorkSpaceProvider
    from ghostos.framework.tasks import WorkspaceTasksProvider
    from ghostos.framework.eventbuses import MemEventBusImplProvider
    from ghostos.framework.llms import ConfigBasedLLMsProvider, PromptStorageInWorkspaceProvider
    from ghostos.framework.logger import DefaultLoggerProvider
    from ghostos.framework.variables import WorkspaceVariablesProvider
    from ghostos.framework.ghostos import GhostOSProvider
    from ghostos.framework.documents import ConfiguredDocumentRegistryProvider
    from ghostos.framework.realtime import ConfigBasedRealtimeProvider
    from ghostos.core.aifunc import DefaultAIFuncExecutorProvider, AIFuncRepoByConfigsProvider
    return [

        # --- logger ---#

        DefaultLoggerProvider(),
        # --- workspace --- #
        BasicWorkspaceProvider(
            workspace_dir=root_dir,
            configs_path=workspace_configs_dir,
            runtime_path=workspace_runtime_dir,
        ),
        WorkspaceConfigsProvider(),
        WorkspaceProcessesProvider(runtime_processes_dir),
        WorkspaceTasksProvider(runtime_tasks_dir),
        ConfiguredDocumentRegistryProvider("documents_registry.yml"),

        WorkspaceVariablesProvider(),
        WorkspaceImageAssetsProvider(),
        WorkspaceAudioAssetsProvider(),

        # --- messages --- #
        DefaultOpenAIParserProvider(),

        # --- session ---#
        MsgThreadsRepoByWorkSpaceProvider(runtime_threads_dir),
        MemEventBusImplProvider(),

        # --- moss --- #
        DefaultMOSSProvider(),

        # --- llm --- #
        ConfigBasedLLMsProvider(),
        PromptStorageInWorkspaceProvider(),

        # --- basic library --- #
        DefaultModulesProvider(),
        ShutdownProvider(),
        # WorkspaceTranslationProvider("translations"),

        # --- aifunc --- #
        DefaultAIFuncExecutorProvider(),
        AIFuncRepoByConfigsProvider(runtime_frame_dir="aifunc_frames"),

        GhostOSProvider(),
        ConfigBasedRealtimeProvider(),
    ]


# --- system bootstrap --- #
def make_app_container(
        workspace_path: str,
        dotenv_file_path: str = ".env",
        app_providers: Optional[List[Provider]] = None,
        app_contracts: Optional[Contracts] = None,
) -> Container:
    """
    make application global container
    """
    # load env from dotenv file
    dotenv.load_dotenv(dotenv_path=join(workspace_path, dotenv_file_path))
    # default logger name for GhostOS application
    if app_providers is None:
        app_providers = default_application_providers(root_dir=workspace_path)
    if app_contracts is None:
        app_contracts = default_application_contracts()

    # prepare application container
    _container = Container(name="ghostos_root")
    _container.register(*app_providers)
    # contracts validation
    app_contracts.validate(_container)
    # bootstrap.
    _container.set(GHOSTOS_VERSION_KEY, GHOSTOS_VERSION)
    _container.bootstrap()
    return _container


application_container = make_app_container(workspace_dir)
""" the global static application container. reset it before application usage"""

ghost_func = init_ghost_func(application_container)
""" the default ghost func on default container"""


def get_ghostos(container: Optional[Container] = None) -> GhostOS:
    if container is None:
        container = application_container
    return container.force_fetch(GhostOS)


def get_container() -> Container:
    return application_container


def reset(con: Container) -> Container:
    """
    reset static ghostos application level instances
    :param con: a container with application level contract bindings, shall be validated outside.
    :return:
    """
    global application_container, ghost_func
    # reset global container
    application_container = con
    # reset global ghost func
    ghost_func = init_ghost_func(application_container)
    return application_container


def reset_at(app_dir: str) -> Container:
    """
    reset application with default configuration at specified app directory
    only run once if app_dir is the same
    """
    global workspace_dir
    if app_dir == workspace_dir:
        return application_container
    workspace_dir = app_dir
    _container = make_app_container(app_dir)
    return reset(_container)


# --- test the module by python -i --- #

if __name__ == '__main__':
    """
    run `python -i __init__.py` to interact with the current file
    """
