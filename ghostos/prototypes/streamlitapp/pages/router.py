from typing import Optional, List
from ghostos.prototypes.streamlitapp.utils.route import Route, Router, Link
from ghostos.core.messages import Message
from ghostos.core.aifunc import ExecFrame
from ghostos.abcd import Ghost, Context
from ghostos_common.entity import EntityMeta, get_entity
from ghostos_common.helpers import generate_import_path
from enum import Enum
from pydantic import Field
from ghostos.framework.llms import LLMsYamlConfig
from ghostos.framework.openai_realtime.configs import OpenAIRealtimeAppConf

__all__ = [
    "Route",
    "Router",
    "default_router",
    "PagePath",
    "GhostTaskRoute",
    "ConfigsRoute",
    "GhostChatRoute",
    "AIFuncListRoute",
    "AIFuncDetailRoute",
    "ShowThreadRoute",
]


class PagePath(str, Enum):
    HOMEPAGE = "ghostos.prototypes.streamlitapp.pages.homepage"
    AIFUNCS = "ghostos.prototypes.streamlitapp.pages.aifuncs"
    GHOSTS = "ghostos.prototypes.streamlitapp.pages.chat_with_ghost"
    THREADS = "ghostos.prototypes.streamlitapp.pages.threads"
    CONFIGS = "ghostos.prototypes.streamlitapp.pages.configs"

    def suffix(self, attr_name: str):
        return self.value + attr_name


# --- ghosts --- #

class GhostTaskRoute(Route):
    link = Link(
        name="Task Info",
        import_path=PagePath.GHOSTS.suffix(":main_task"),
        streamlit_icon=":material/smart_toy:",
        button_help="todo",
        antd_icon="robot",
    )
    task_id: str = Field(default="", description="task id")


class ShowThreadRoute(Route):
    link = Link(
        name="Thread Info",
        import_path=PagePath.THREADS.suffix(":show_thread"),
        streamlit_icon=":material/smart_toy:",
        button_help="show details of a thread",
        antd_icon="robot",
    )
    thread_id: str = Field(default="", description="thread id or file name")
    task_id: str = Field(default="", description="chat task id")


class GhostChatRoute(Route):
    link = Link(
        name="Chat",
        import_path=PagePath.GHOSTS.suffix(":main_chat"),
        streamlit_icon=":material/smart_toy:",
        button_help="todo",
        antd_icon="robot",
    )
    task_id: str = Field(default="", description="Ghost Task ID")
    filename: Optional[str] = Field(default=None, description="filename to lunch the ghost")
    camera_input: bool = Field(default=False, description="camera input")
    image_input: bool = Field(default=False, description="image input")
    auto_run: bool = Field(default=True, description="auto run")
    realtime: bool = Field(default=False, description="realtime")
    vad_mode: bool = Field(default=True, description="vad mode")
    listen_mode: bool = Field(default=True, description="listening")

    def generate_key(self, session_state, key: str) -> str:
        turn = self.get_render_turn(session_state)
        return generate_import_path(self.__class__) + "-turn-" + str(turn) + "-key-" + key

    def media_input(self) -> bool:
        return self.camera_input or self.image_input

    def get_render_turn(self, session_state) -> int:
        key = generate_import_path(self.__class__) + ":turn"
        if key not in session_state:
            session_state[key] = 0
        return session_state[key]

    def new_render_turn(self, session_state) -> int:
        key = generate_import_path(self.__class__) + ":turn"
        if key not in session_state:
            session_state[key] = 0
        session_state[key] += 1
        return session_state[key]


# --- configs --- #

class ConfigsRoute(Route):
    link = Link(
        name="Configs",
        import_path=PagePath.CONFIGS.suffix(":main"),
        streamlit_icon=":material/settings:",
        button_help="todo",
        antd_icon="settings",
    )
    config_classes: List[str] = Field(
        default_factory=lambda: [
            generate_import_path(LLMsYamlConfig),
            generate_import_path(OpenAIRealtimeAppConf),
        ],
        description="config classes"
    )


# --- home --- #

class Home(Route):
    link = Link(
        name="GhostOS",
        import_path=PagePath.HOMEPAGE.suffix(":home"),
        streamlit_icon=":material/home:",
        button_help="help",
        antd_icon="house-fill",
    )


class Navigator(Route):
    link = Link(
        name="Navigator",
        import_path=PagePath.HOMEPAGE.suffix(":navigator"),
        streamlit_icon=":material/home:",
        antd_icon="box-fill",
    )


class GhostOSHost(Route):
    link = Link(
        name="GhostOS Host",
        import_path=PagePath.HOMEPAGE.suffix(":ghostos_host"),
        streamlit_icon=":material/smart_toy:",
    )


class Helloworld(Route):
    """
    test only
    """
    link = Link(
        name="Hello World",
        import_path=PagePath.HOMEPAGE.suffix(":helloworld"),
        streamlit_icon=":material/home:",
    )


# --- ai functions --- #

class AIFuncListRoute(Route):
    link = Link(
        name="AIFunc List",
        import_path=PagePath.AIFUNCS.suffix(".index:main"),
        streamlit_icon=":material/functions:",
    )
    search: str = Field(
        default="",
        description="search ai functions with keyword",
    )


class AIFuncDetailRoute(Route):
    link = Link(
        name="AIFunc Detail",
        import_path=PagePath.AIFUNCS.suffix(".detail:main"),
        streamlit_icon=":material/functions:",
    )
    aifunc_id: str = Field(
        default="",
        description="AIFunc ID, which is import path of it",
    )
    frame: Optional[ExecFrame] = Field(
        default=None,
        description="current execution frame",
    )
    executed: bool = False
    received: List[Message] = Field(
        default_factory=list,
        description="list of execution messages",
    )
    timeout: float = 40
    exec_idle: float = 0.2

    def clear_execution(self):
        self.executed = False
        self.received = []
        self.frame = None


# --- routers --- #

def default_router() -> Router:
    return Router(
        [
            Home(),
            Helloworld(),
            Navigator(),
            GhostOSHost(),
            AIFuncListRoute(),
            AIFuncDetailRoute(),
            # ghosts
            GhostChatRoute(),
            GhostTaskRoute(),
            ShowThreadRoute(),

            ConfigsRoute(),
        ],
        home=Home.label(),
        navigator_page_names=[
            ConfigsRoute.label(),
        ],
        default_menu={
            Home.label(): None,
        },
        default_sidebar_buttons=[
        ],
    )
