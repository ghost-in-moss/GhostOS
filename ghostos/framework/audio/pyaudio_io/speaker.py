try:
    from pyaudio import PyAudio, paInt16
except ImportError:
    raise ImportError(f"Pyaudio is required, please install pyaudio or ghostos[audio] first")

from typing import Optional
from io import BytesIO
from ghostos.abcd.realtime import Speaker


class PyAudioSpeaker(Speaker):

    def __init__(self):
        self.stream: Optional[PyAudio.Stream] = None
        self.buffer: Optional[BytesIO] = None

    def __enter__(self):
        if self.stream is not None:
            raise RuntimeError("PyAudioSpeaker already initialized")
        self.buffer = BytesIO()
        self.stream = PyAudio().open(
            format=paInt16,
            channels=1,
            rate=44100,
            output=True,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            self.buffer = None

    def speak(self, data: bytes):
        if self.stream is None:
            raise RuntimeError("PyAudioSpeaker is not started in context manager")
        self.stream.write(data)

    def flush(self) -> bytes:
        if self.buffer is None:
            return bytes()
        value = self.buffer.getvalue()
        self.buffer.close()
        self.buffer = None
        return value
