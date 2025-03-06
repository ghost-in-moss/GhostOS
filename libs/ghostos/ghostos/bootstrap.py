from __future__ import annotations

import os
import sys

import yaml
from warnings import warn
from typing import List, Optional, Tuple, Union
from os.path import dirname, join, exists, abspath, isdir
from ghostos.abcd import GhostOS
from ghostos_container import Container, Provider, Contracts
from ghostos.prototypes.ghostfunc import init_ghost_func, GhostFunc
from pydantic import BaseModel, Field

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
    'workspace_stub_dir',
    'BootstrapConfig',
    'get_bootstrap_config',

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
    'make_app_container',

    # reset ghostos default application instances.
    'reset',
    'get_container',

    # default configuration
    # consider safety reason, ghostos is not ready for online business
    # so many abilities shall be forbidden to web agent
    'default_application_contracts',
    'default_application_providers',

    'get_ghostos',

    # >>> GhostFunc
    # is a test library, which is able to define dynamic code for an in-complete function.
    # We develop it for early experiments.
    # Check example_ghost_func.py
    # <<<
    'GhostFunc',
    'init_ghost_func',

]

_application_container = None

DEFAULT_WORKSPACE_DIR = "ghostos_ws"
WORKSPACE_STUB = "workspace_stub"


# --- prepare application paths --- #


def expect_workspace_dir() -> Tuple[str, bool]:
    """
    :return: (workspace dir: str, exists: bool)
    """
    expect_dir = abspath(DEFAULT_WORKSPACE_DIR)
    return expect_dir, exists(expect_dir) and isdir(expect_dir)


def workspace_stub_dir() -> str:
    return join(dirname(__file__), WORKSPACE_STUB)


def find_workspace_dir() -> str:
    expected, ok = expect_workspace_dir()
    if ok:
        return expected
    return workspace_stub_dir()


class BootstrapConfig(BaseModel):
    workspace_dir: str = Field(
        default=DEFAULT_WORKSPACE_DIR,
        description="ghostos relative workspace directory",
    )
    dotenv_file_path: str = Field(".env", description="ghostos workspace .env file")
    workspace_configs_dir: str = Field(
        "configs",
        description="ghostos workspace relative path for configs directory",
    )
    workspace_runtime_dir: str = Field(
        "runtime",
        description="ghostos workspace relative path for runtime directory",
    )
    python_paths: List[str] = Field(
        default_factory=list,
        description="load the python path to sys.path"
    )
    app_container_maker: Union[str, None] = Field(
        default=None,
        description="import path to generate ghostos app container, Callable[[], Container]",
    )

    __from_file__: str = ""

    @staticmethod
    def abs_ghostos_dir() -> str:
        return dirname(dirname(__file__))

    def abs_workspace_dir(self) -> str:
        app_dir = abspath(self.workspace_dir)
        if exists(app_dir) and isdir(app_dir):
            return app_dir
        return find_workspace_dir()

    def abs_runtime_dir(self) -> str:
        workspace_dir = self.abs_workspace_dir()
        return join(workspace_dir, "runtime")

    def abs_assets_dir(self) -> str:
        workspace_dir = self.abs_workspace_dir()
        return join(workspace_dir, "assets")

    def env_file(self) -> str:
        workspace_dir = self.abs_workspace_dir()
        return join(workspace_dir, self.dotenv_file_path)

    def env_example_file(self) -> str:
        workspace_dir = self.abs_workspace_dir()
        return join(workspace_dir, ".example.env")

    def save(self, dir_path: str = None) -> str:
        from ghostos_common.helpers import yaml_pretty_dump
        if dir_path is None:
            filename = join(abspath(".ghostos.yml"))
        else:
            filename = join(dir_path, ".ghostos.yml")
        content = yaml_pretty_dump(self.model_dump())
        with open(filename, "w") as f:
            f.write(content)
        return filename


def get_bootstrap_config(local: bool = True) -> BootstrapConfig:
    """
    get ghostos bootstrap config from current working directory
    if not found, return default configs.
    """
    expect_file = abspath(".ghostos.yml")
    if local and exists(expect_file):
        with open(expect_file) as f:
            content = f.read()
            data = yaml.safe_load(content)
            conf = BootstrapConfig(**data)
            conf.__from_file__ = expect_file
            return conf
    else:
        return BootstrapConfig()


# --- default providers --- #


def default_application_contracts() -> Contracts:
    """
    Application level contracts
    """
    from ghostos_moss import MossCompiler
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
        config: Optional[BootstrapConfig] = None,
) -> List[Provider]:
    """
    application default providers
    todo: use manager provider to configurate multiple kinds of implementation
    """
    from ghostos.contracts.shutdown import ShutdownProvider
    from ghostos.contracts.modules import DefaultModulesProvider
    from ghostos_moss import DefaultMOSSProvider
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

    # session level libraries
    from ghostos.libraries.replier import ReplierImplProvider
    from ghostos.libraries.pyeditor import SimplePyInterfaceGeneratorProvider

    if config is None:
        config = get_bootstrap_config(local=True)

    return [

        # --- logger ---#

        DefaultLoggerProvider(),
        # --- workspace --- #
        BasicWorkspaceProvider(
            workspace_dir=config.abs_workspace_dir(),
            configs_path=config.workspace_configs_dir,
            runtime_path=config.workspace_runtime_dir,
        ),
        WorkspaceConfigsProvider(),
        WorkspaceProcessesProvider(),
        WorkspaceTasksProvider(),
        ConfiguredDocumentRegistryProvider(),
        WorkspaceVariablesProvider(),
        WorkspaceImageAssetsProvider(),
        WorkspaceAudioAssetsProvider(),

        # --- messages --- #
        DefaultOpenAIParserProvider(),

        # --- session ---#
        MsgThreadsRepoByWorkSpaceProvider(),
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
        AIFuncRepoByConfigsProvider(),

        GhostOSProvider(),
        ConfigBasedRealtimeProvider(),

        # --- system default session level libraries --- #
        ReplierImplProvider(),
        SimplePyInterfaceGeneratorProvider(),
    ]


# --- system bootstrap --- #
def make_app_container(
        *,
        bootstrap_conf: Optional[BootstrapConfig] = None,
        app_providers: Optional[List[Provider]] = None,
        app_contracts: Optional[Contracts] = None,
) -> Container:
    """
    make application global container
    """
    if bootstrap_conf is None:
        bootstrap_conf = get_bootstrap_config(local=True)

    # default logger name for GhostOS application
    if app_providers is None:
        app_providers = default_application_providers(bootstrap_conf)
    if app_contracts is None:
        app_contracts = default_application_contracts()

    # prepare application container
    _container = Container(name="ghostos_root")
    _container.set(BootstrapConfig, bootstrap_conf)
    _container.register(*app_providers)
    # contracts validation
    app_contracts.validate(_container)
    return _container


def bootstrap() -> Container:
    bootstrap_conf = get_bootstrap_config(local=True)
    workspace_dir = bootstrap_conf.workspace_dir
    if workspace_dir.startswith(bootstrap_conf.abs_ghostos_dir()):
        warn(
            f"GhostOS workspace dir is not found, better run `ghostos init` at first."
            f"Currently using `{workspace_dir}` as workspace."
        )

    if bootstrap_conf.python_paths:
        cwd = os.getcwd()
        for python_path in bootstrap_conf.python_paths:
            real_path = abspath(join(cwd, python_path))
            sys.path.append(real_path)

    # load env from dotenv file
    env_path = join(bootstrap_conf.workspace_dir, bootstrap_conf.dotenv_file_path)
    if exists(env_path):
        import dotenv
        dotenv.load_dotenv(dotenv_path=env_path)

    # use app container maker to make a container.
    if bootstrap_conf.app_container_maker:
        from ghostos_common.helpers import import_from_path
        maker = import_from_path(bootstrap_conf.app_container_maker)
        container = maker()
    else:
        container = make_app_container(bootstrap_conf=bootstrap_conf)
    # bootstrap.
    container.bootstrap()
    return container


def get_ghostos(container: Optional[Container] = None) -> GhostOS:
    if container is None:
        container = bootstrap()
    return container.force_fetch(GhostOS)


def get_container() -> Container:
    global _application_container
    if _application_container is None:
        _application_container = bootstrap()
    return _application_container


def reset(con: Container) -> Container:
    """
    reset static ghostos application level instances
    :param con: a container with application level contract bindings, shall be validated outside.
    :return:
    """
    global _application_container
    # reset global container
    _application_container = con
    # reset global ghost func
    return _application_container

# --- test the module by python -i --- #
