from ghostos.abcd.realtime import Speaker, Listener


def get_pyaudio_pcm16_listener(rate: int = 24000) -> Listener:
    from ghostos.framework.audio.pyaudio_io.listener import PyAudioPCM16Listener
    return PyAudioPCM16Listener(rate)


def get_pyaudio_pcm16_speaker(rate: int = 24000, buffer_size: int = 4096) -> Speaker:
    from ghostos.framework.audio.pyaudio_io.speaker import PyAudioPCM16Speaker
    return PyAudioPCM16Speaker(rate, buffer_size)
