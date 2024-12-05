try:
    from pyaudio import PyAudio, paInt16
except ImportError:
    raise ImportError(f"Pyaudio is required, please install pyaudio or ghostos[audio] first")

from typing import Optional
from io import BytesIO
from ghostos.abcd.realtime import Listener

CHUNK = 1024
FORMAT = paInt16
CHANNELS = 1
RATE = 44100


class PyAudioListener(Listener):

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
            input=True,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            self.buffer = None

    def hearing(self, second: float = 1) -> Optional[bytes]:
        if self.stream is None:
            return None
        sending_buffer = BytesIO()
        for i in range(0, int((RATE / CHUNK) * second)):
            data = self.stream.read(CHUNK)
            sending_buffer.write(data)
            self.buffer.write(data)

        return sending_buffer.getvalue()

    def flush(self) -> bytes:
        if self.buffer is None:
            return bytes()
        value = self.buffer.getvalue()
        self.buffer.close()
        self.buffer = None
        return value
