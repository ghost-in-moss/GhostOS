try:
    from pyaudio import PyAudio, paInt16
except ImportError:
    raise ImportError(f"Pyaudio is required, please install pyaudio or ghostos[audio] first")

from typing import Callable, Union
from ghostos.abcd.realtime import Listener, Listening
from threading import Thread, Event
from io import BytesIO

CHUNK = 1024
FORMAT = paInt16
CHANNELS = 1
RATE = 44100


class PyAudioPCM16Listener(Listener):

    def __init__(self, rate: int = 24000, chunk_size: int = CHUNK):
        self.rate = rate
        self.chunk_size = chunk_size
        self.stream = PyAudio().open(
            format=paInt16,
            channels=1,
            rate=self.rate,
            input=True,
        )

    def listen(self, sender: Callable[[bytes], None]) -> Listening:
        return PyAudioPCM16Listening(self.stream, sender, self.rate, self.chunk_size)

    def __del__(self):
        self.stream.close()


class PyAudioPCM16Listening(Listening):

    def __init__(self, stream, sender: Callable[[bytes], None], rate: int = 24000, chunk: int = CHUNK):
        self.sender = sender
        self.stream = stream
        self.rate = rate
        self.chunk = chunk
        self.stopped = Event()
        self.thread = Thread(target=self._listening)

    def _listening(self):
        self.stream.start_stream()
        while not self.stopped.is_set():
            buffer = BytesIO()
            for i in range(int(self.rate / self.chunk * 0.5)):
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                buffer.write(data)
            self.sender(buffer.getvalue())
        self.stream.stop_stream()

    def __enter__(self):
        self.thread.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stopped.set()
        self.thread.join()
