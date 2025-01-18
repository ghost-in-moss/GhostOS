from pyaudio import PyAudio, paInt16
from scipy.signal import resample

import numpy as np
from typing import Callable, Union
from ghostos.abcd.realtime import Speaker, Speaking
from threading import Thread, Event


class PyAudioPCM16Speaker(Speaker):

    def __init__(
            self,
            input_rate: int = 24000,
            output_rate: int = 24000,
            buffer_size: int = 4096,
            channels: int = 1,
            output_device_index: Union[int, None] = None,
    ):
        self.input_rate = input_rate
        self.output_rate = output_rate
        self.buffer_size = buffer_size
        self.stream = PyAudio().open(
            format=paInt16,
            channels=channels,
            rate=self.output_rate,
            output=True,
            output_device_index=output_device_index,
        )

    def speak(self, queue: Callable[[], Union[bytes, None]]) -> Speaking:
        return PyAudioPCM16Speaking(self.stream, queue, self.input_rate, self.output_rate, self.buffer_size)

    def __del__(self):
        self.stream.close()


class PyAudioPCM16Speaking(Speaking):

    def __init__(
            self,
            stream,
            queue: Callable[[], Union[bytes, None]],
            input_rate: int = 24000,
            output_rate: int = 24000,
            buffer_size: int = 0,
    ):
        self.stream = stream
        self.input_rate = input_rate
        self.output_rate = output_rate
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
            parsed = self._parse_output_data(data)
            self.stream.write(parsed)
        self._done = True

    def _parse_output_data(self, data: bytes) -> bytes:
        if self.input_rate == self.output_rate:
            return data
        audio_data = np.frombuffer(data, dtype=np.int16)
        num_samples = int(len(audio_data) * self.output_rate / self.input_rate)

        # 使用 resample 进行重新采样
        resampled_audio = resample(audio_data, num_samples)

        # 导出为二进制数据
        return resampled_audio.astype(np.int16)

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
