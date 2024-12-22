try:
    from pyaudio import PyAudio, paInt16
except ImportError:
    raise ImportError(f"Pyaudio is required, please install pyaudio or ghostos[audio] first")

from typing import Callable, Union
from ghostos.abcd.realtime import Speaker, Speaking
from threading import Thread, Event


class PyAudioPCM16Speaker(Speaker):

    def __init__(self, rate: int = 24000, buffer_size: int = 4096):
        self.rate = rate
        self.buffer_size = buffer_size
        self.stream = PyAudio().open(
            format=paInt16,
            channels=1,
            rate=self.rate,
            output=True,
        )

    def speak(self, queue: Callable[[], Union[bytes, None]]) -> Speaking:
        return PyAudioPCM16Speaking(self.stream, queue, self.rate, self.buffer_size)

    def __del__(self):
        self.stream.close()


class PyAudioPCM16Speaking(Speaking):

    def __init__(self, stream, queue: Callable[[], Union[bytes, None]], rate: int = 24000, buffer_size: int = 0):
        self.stream = stream
        self.rate = rate
        self.buffer_size = buffer_size
        self.queue = queue
        self.stop = Event()
        self.thread = Thread(target=self._speaking)
        self._done = False
        self._joined = False

    def _speaking(self):
        self.stream.start_stream()
        while not self.stop.is_set():
            data = self.queue()
            if not data:
                break
            self.stream.write(data)
        self._done = True

    def __enter__(self):
        self.thread.start()
        return self

    def wait(self):
        if self._joined:
            return
        self.thread.join()
        self._joined = True

    def done(self) -> bool:
        return self._done

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop.set()
        self.wait()
