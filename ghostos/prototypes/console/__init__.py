from os.path import join, dirname
from typing import Optional, List
from ghostos.core import GhostOS
from ghostos.framework.ghostos import demo_ghostos, DemoGhostOS
from ghostos.framework.ghosts.demo import DemoGhostConf
from ghostos.prototypes.console.app import ConsolePrototype
from ghostos.core.ghosts import Thought
from ghostos.helpers import get_calling_modulename, import_from_path, md5, uuid
from ghostos.container import Provider

__all__ = [
    'ConsoleApp',
    'ConsolePrototype',
    'quick_new_console_app',
    'demo_console_app',
]


class ConsoleApp:
    """
    Create a GhostOS Console app with a ghostos.
    New demo from specific directory as default.
    """

    def __init__(
            self,
            ghostos: GhostOS = None,
    ):
        self._ghostos = ghostos
        # status
        self._ran_thought = False
        self._ran_console = False

    @classmethod
    def new_demo(
            cls,
            *,
            root_dir: str,
            logger_conf_path: str,
            logger_name: str = "debug",
            conf_path: str = "configs",
            runtime_path: str = "runtime",
            processes_path: str = "processes",
            tasks_path: str = "tasks",
            threads_path: str = "threads",
            llm_conf_path: str = "llms_conf.yml",
            source_path: str = "src",
    ):
        ghostos = DemoGhostOS(
            root_dir=root_dir,
            logger_conf_path=logger_conf_path,
            logger_name=logger_name,
            config_path=conf_path,
            runtime_path=runtime_path,
            source_path=source_path,
            processes_path=processes_path,
            tasks_path=tasks_path,
            threads_path=threads_path,
            llm_config_path=llm_conf_path,
        )
        return cls(ghostos)

    def with_providers(self, providers: List[Provider]):
        """
        register global providers
        :param providers: provide contracts and implementations.
        """
        for provider in providers:
            self._ghostos.container().register(provider)

    def run_console(
            self,
            ghost_id: str,
            *,
            username: str = "BrightRed",
            on_create_message: Optional[str] = None,
            debug: bool = False,
            session_id: Optional[str] = None,
            welcome_user_message: Optional[str] = None,
    ):
        """
        :param ghost_id: should exist in configs/ghosts.yml
        :param username: the username, default is my name haha.
        :param on_create_message: the message to send to the assistant as default.
        :param debug: if debug is True, render more verbosely.
        :param session_id: if given, the console will start in the same session by the id.
        :param welcome_user_message: if on_create_message is None, use welcome_user_message let agent welcome first
        """
        if self._ran_console:
            return
        self._ran_console = True
        ghostos = demo_ghostos
        console_impl = ConsolePrototype(
            ghostos=ghostos,
            ghost_id=ghost_id,
            username=username,
            debug=debug,
            on_create_message=on_create_message,
            session_id=session_id,
            welcome_user_message=welcome_user_message,
        )
        console_impl.run()
        self._ran_console = False

    def run_thought(
            self,
            thought: Thought,
            *,
            instruction: Optional[str] = None,
            username: str = "BrightRed",
            ghost_name: str = "GhostOSDemo",
            debug: bool = False,
            meta_prompt: str = "",
            long_term_session: bool = False,
            welcome_user_message: Optional[str] = None,
    ):
        """
        Run a thought instead of run a defined Ghost.
        :param thought: root thought of the ghost
        :param instruction: the init instruction send to assistant
        :param username: name of the console's user. default is my name hahaha.
        :param ghost_name: ghost name
        :param debug: if debug is True, render more verbosely.
        :param meta_prompt: define the meta prompt of the ghost. I leave it empty.
        :param long_term_session: if true, session id is always related to the calling module.
        :param welcome_user_message: if on_create_message is None, use welcome_user_message let agent welcome first
        :return:
        """
        if self._ran_thought:
            return
        self._ran_thought = True
        modulename = get_calling_modulename(1)
        module = import_from_path(modulename)
        file = module.__file__
        ghost_id = md5(file)
        ghost_conf = DemoGhostConf(
            id=ghost_id,
            name=ghost_name,
            thought_meta=thought.to_entity_meta(),
            meta_prompt=meta_prompt,
        )
        self._ghostos.register(ghost_conf)
        if long_term_session:
            session_id = ghost_id
        else:
            session_id = uuid()
        console_impl = ConsolePrototype(
            ghostos=self._ghostos,
            ghost_id=ghost_id,
            username=username,
            on_create_message=instruction,
            debug=debug,
            session_id=session_id,
            welcome_user_message=welcome_user_message,
        )
        console_impl.run()
        self._ran_thought = False


demo_dir = join(dirname(dirname(dirname(__file__))), "demo")

demo_console_app = ConsoleApp.new_demo(
    root_dir=demo_dir,
    logger_conf_path=join(demo_dir, "configs/logging.yml"),
)
""" default app instance for testing convenient"""

__app__ = None


def quick_new_console_app(
        current_file: str,
        dirname_times: int = 0,
        logging_conf: str = "configs/logging.yml",
        **kwargs,
) -> ConsoleApp:
    """
    quick to create a console app based on root_dir. only once shall be called globally.
    :param current_file: current file name, usually __file__
    :param dirname_times: depth from current_file to root dir
    :param logging_conf:
    :return:
    """
    global __app__
    if __app__ is not None:
        return __app__
    root_dir = current_file
    for i in range(dirname_times):
        root_dir = dirname(root_dir)

    logger_conf_path = join(root_dir, logging_conf)
    app = ConsoleApp.new_demo(root_dir=root_dir, logger_conf_path=logger_conf_path, **kwargs)
    __app__ = app
    return app
