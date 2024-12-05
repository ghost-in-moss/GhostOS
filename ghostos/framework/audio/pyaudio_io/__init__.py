from ghostos.abcd.realtime import Speaker, Listener


def get_pyaudio_listener() -> Listener:
    from ghostos.framework.audio.pyaudio_io.listener import Listener
    return Listener()


def get_pyaudio_speaker() -> Speaker:
    from ghostos.framework.audio.pyaudio_io.speaker import Speaker
    return Speaker()
