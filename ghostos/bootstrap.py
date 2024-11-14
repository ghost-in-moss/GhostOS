from typing import List, Optional
from os.path import dirname, join
from ghostos.core.abcd import GhostOS
from ghostos.container import Container, Provider, Contracts
from ghostos.contracts.logger import config_logging
from ghostos.prototypes.ghostfunc import init_ghost_func, GhostFunc
import dotenv
import os

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

    # default configuration
    'application_dir',
    'default_application_contracts',
    'default_application_providers',
]

# --- prepare application paths --- #


application_dir = join(dirname(dirname(__file__)), 'app')
"""application root directory path"""


# --- default providers --- #


def default_application_contracts() -> Contracts:
    """
    Application level contracts
    """
    from ghostos.core.moss import MossCompiler
    from ghostos.core.messages.openai import OpenAIMessageParser
    from ghostos.contracts.pool import Pool
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
    from ghostos.core.aifunc import AIFuncExecutor, AIFuncRepository

    return Contracts([
        # workspace contracts
        Workspace,  # application workspace implementation
        Configs,  # application configs repository
        Variables,

        # system contracts
        Pool,  # multi-thread or process pool to submit async tasks
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
    ])


def default_application_providers(
        root_dir: str,
        logger_name: str,
        workspace_configs_dir: str = "configs",
        workspace_runtime_dir: str = "runtime",
        runtime_processes_dir: str = "processes",
        runtime_tasks_dir: str = "tasks",
        runtime_threads_dir: str = "threads",
        llms_conf_path: str = "llms_conf.yml",
) -> List[Provider]:
    """
    application default providers
    todo: use manager provider to configurate multiple kinds of implementation
    """
    from ghostos.contracts.pool import DefaultPoolProvider
    from ghostos.contracts.shutdown import ShutdownProvider
    from ghostos.contracts.modules import DefaultModulesProvider
    from ghostos.core.moss import DefaultMOSSProvider
    from ghostos.core.messages.openai import DefaultOpenAIParserProvider
    from ghostos.framework.workspaces import BasicWorkspaceProvider
    from ghostos.framework.configs import WorkspaceConfigsProvider
    from ghostos.framework.processes import WorkspaceProcessesProvider
    from ghostos.framework.threads import MsgThreadsRepoByWorkSpaceProvider
    from ghostos.framework.tasks import WorkspaceTasksProvider
    from ghostos.framework.eventbuses import MemEventBusImplProvider
    from ghostos.framework.llms import ConfigBasedLLMsProvider, PromptStorageInWorkspaceProvider
    from ghostos.framework.logger import NamedLoggerProvider
    from ghostos.framework.variables import WorkspaceVariablesProvider
    from ghostos.framework.ghostos import GhostOSProvider
    from ghostos.core.aifunc import DefaultAIFuncExecutorProvider, AIFuncRepoByConfigsProvider
    from ghostos.framework.documents import ConfiguredDocumentRegistryProvider
    return [

        # --- logger ---#

        NamedLoggerProvider(logger_name),
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

        # --- messages --- #
        DefaultOpenAIParserProvider(),

        # --- session ---#
        MsgThreadsRepoByWorkSpaceProvider(runtime_threads_dir),
        DefaultPoolProvider(100),
        MemEventBusImplProvider(),

        # --- moss --- #
        DefaultMOSSProvider(),

        # --- llm --- #
        ConfigBasedLLMsProvider(llms_conf_path),
        PromptStorageInWorkspaceProvider(),

        # --- basic library --- #
        DefaultModulesProvider(),
        ShutdownProvider(),
        # WorkspaceTranslationProvider("translations"),

        # --- aifunc --- #
        DefaultAIFuncExecutorProvider(),
        AIFuncRepoByConfigsProvider(runtime_frame_dir="aifunc_frames"),

        GhostOSProvider()
    ]


# --- system bootstrap --- #
def make_app_container(
        app_dir: str,
        logging_conf_path: str = "configs/logging.yml",
        dotenv_file_path: str = ".env",
        app_providers: Optional[List[Provider]] = None,
        app_contracts: Optional[Contracts] = None,
) -> Container:
    """
    make application global container
    :param app_dir:
    :param logging_conf_path:
    :param dotenv_file_path:
    :param app_providers:
    :param app_contracts:
    :return:
    """
    # load env from dotenv file
    dotenv.load_dotenv(dotenv_path=join(app_dir, dotenv_file_path))
    logging_conf_path = join(app_dir, logging_conf_path)
    # default logger name for GhostOS application
    logger_name = os.environ.get("LoggerName", "debug")
    # initialize logging configs
    config_logging(logging_conf_path)
    # todo: i18n install

    if app_providers is None:
        app_providers = default_application_providers(root_dir=application_dir, logger_name=logger_name)
    if app_contracts is None:
        app_contracts = default_application_contracts()

    # prepare application container
    _container = Container()
    _container.register(*app_providers)
    # contracts validation
    app_contracts.validate(_container)
    # bootstrap.
    _container.bootstrap()
    return _container


application_container = make_app_container(application_dir)
""" the global static application container. reset it before application usage"""

ghost_func = init_ghost_func(application_container)
""" the default ghost func on default container"""


def get_ghostos(container: Optional[Container] = None) -> GhostOS:
    if container is None:
        container = application_container
    return container.force_fetch(GhostOS)


def reset(con: Container) -> None:
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


def reset_at(app_dir: str) -> None:
    """
    reset application with default configuration at specified app directory
    only run once if app_dir is the same
    """
    global application_dir
    if app_dir == application_dir:
        return
    application_dir = app_dir
    _container = make_app_container(app_dir)
    reset(_container)


# --- test the module by python -i --- #

if __name__ == '__main__':
    """
    run `python -i __init__.py` to interact with the current file
    """
