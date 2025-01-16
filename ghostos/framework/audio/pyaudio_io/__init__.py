from typing import Union
from ghostos.abcd.realtime import Speaker, Listener


def get_pyaudio_pcm16_listener(
        rate: int = 24000,
        output_rate: int = 24000,
        interval: float = 0.5,
        channels: int = 1,
        chunk_size: int = 1024,
        input_device_index: Union[int, None] = None,
) -> Listener:
    try:
        import pyaudio
    except ImportError:
        raise ImportError(f"pyaudio package is required. run `pip install ghostos[audio]`")
    from ghostos.framework.audio.pyaudio_io.listener import PyAudioPCM16Listener
    return PyAudioPCM16Listener(
        sample_rate=rate,
        output_rate=output_rate,
        interval=interval,
        channels=channels,
        chunk_size=chunk_size,
        input_device_index=input_device_index,
    )


def get_pyaudio_pcm16_speaker(
        input_rate: int = 24000,
        output_rate: int = 24000,
        buffer_size: int = 1024 * 5,
        channels: int = 1,
        output_device_index: Union[int, None] = None,
) -> Speaker:
    try:
        import pyaudio
    except ImportError:
        raise ImportError(f"pyaudio package is required. run `pip install ghostos[audio]`")
    from ghostos.framework.audio.pyaudio_io.speaker import PyAudioPCM16Speaker
    return PyAudioPCM16Speaker(
        input_rate=input_rate,
        output_rate=output_rate,
        buffer_size=buffer_size,
        channels=channels,
        output_device_index=output_device_index,
    )
