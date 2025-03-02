try:
    from pyaudio import PyAudio, paInt16
    from scipy.signal import resample
except ImportError:
    raise ImportError(f"Pyaudio is required, please install pyaudio or ghostos[audio] first")

import numpy as np
from typing import Callable, Optional
from ghostos.abcd.realtime import Listener, Listening
from threading import Thread, Event
from io import BytesIO

CHUNK = 1024
FORMAT = paInt16
CHANNELS = 1
RATE = 44100


class PyAudioPCM16Listener(Listener):

    def __init__(
            self,
            sample_rate: int = 24000,
            output_rate: int = 24000,
            chunk_size: int = CHUNK,
            interval: float = 0.5,
            channels: int = CHANNELS,
            input_device_index: Optional[int] = None,
    ):
        self.sample_rate = sample_rate
        self.output_rate = output_rate
        self.chunk_size = chunk_size
        self.stream = PyAudio().open(
            format=paInt16,
            channels=channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=input_device_index,
        )
        self.interval = interval

    def listen(self, sender: Callable[[bytes], None]) -> Listening:
        return PyAudioPCM16Listening(self.stream, sender, self.sample_rate, self.output_rate, self.chunk_size,
                                     self.interval)

    def __del__(self):
        self.stream.close()


class PyAudioPCM16Listening(Listening):

    def __init__(
            self,
            stream,
            sender: Callable[[bytes], None],
            sample_rate: int = 24000,
            output_rate: int = 24000,
            chunk: int = CHUNK,
            interval: float = 0.5,
    ):
        self.sender = sender
        self.stream = stream
        self.interval = interval
        self.sample_rate = sample_rate
        self.output_rate = output_rate
        self.chunk = chunk
        self.stopped = Event()
        self.thread = Thread(target=self._listening)

    def _listening(self):
        self.stream.start_stream()
        while not self.stopped.is_set():
            buffer = BytesIO()
            for i in range(int((self.sample_rate / self.chunk) * self.interval)):
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                buffer.write(data)
            parsed = self._parse_output_data(buffer.getvalue())
            self.sender(parsed)
        self.stream.stop_stream()

    def _parse_output_data(self, data: bytes) -> bytes:
        if self.sample_rate == self.output_rate:
            return data
        audio_data = np.frombuffer(data, dtype=np.int16)
        num_samples = int(len(audio_data) * self.output_rate / self.sample_rate)

        # 使用 resample 进行重新采样
        resampled_audio = resample(audio_data, num_samples)

        # 导出为二进制数据
        return resampled_audio.astype(np.int16)

    def __enter__(self):
        self.thread.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stopped.set()
        self.thread.join()
