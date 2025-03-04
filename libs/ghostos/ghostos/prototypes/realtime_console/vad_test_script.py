from ghostos.framework.openai_realtime.app import RealtimeAppImpl
from ghostos.framework.openai_realtime.configs import OpenAIRealtimeAppConf
from ghostos.bootstrap import get_ghostos
from ghostos.contracts.configs import Configs
from ghostos.contracts.logger import LoggerItf, get_console_logger
from ghostos.ghosts import Chatbot
from ghostos.framework.audio import get_pyaudio_pcm16_speaker, get_pyaudio_pcm16_listener
from rich.console import Console
import time

console = Console()

if __name__ == "__main__":
    ghostos = get_ghostos()
    logger = get_console_logger(debug=True)
    ghostos_container().set(LoggerItf, logger)
    configs = ghostos_container().force_fetch(Configs)
    app_conf = configs.get(OpenAIRealtimeAppConf)
    # app_conf.listening = False
    app_conf.ws_conf.proxy = "socks5://127.0.0.1:1080"
    jojo = Chatbot(
        name="jojo",
        description="a chatbot for baseline test",
        persona="you are an LLM-driven cute girl, named jojo",
        instruction="remember talk to user with user's language."
    )
    shell = ghostos.create_matrix("realtime_test")
    conversation = shell.sync(jojo)
    realtime_app = RealtimeAppImpl(
        conf=app_conf,
        vad_mode=True,
        conversation=conversation,
        listener=get_pyaudio_pcm16_listener(),
        speaker=get_pyaudio_pcm16_speaker(),
    )
    listening = False

    with realtime_app:
        messages = realtime_app.history_messages()
        logger.info("render history messages")
        for message in messages:
            logger.info("render message %r", message)

        while not realtime_app.is_closed():
            state, operators = realtime_app.state()
            logger.info("state: %s, operators: %r", state, operators)
            buffer = realtime_app.output()
            if buffer is None:
                time.sleep(0.5)
                continue
            logger.info("receive buffer")
            while buffer is not None:
                for chunk in buffer.chunks():
                    logger.info("receive chunk %s", chunk.content)
                tail = buffer.tail()
                logger.info("receive tail %r", tail)
                buffer = buffer.next()
