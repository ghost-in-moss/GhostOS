from typing import Union
from ghostos.framework.audio.pyaudio_io.listener import PyAudioPCM16Listener
from ghostos.framework.audio.pyaudio_io.speaker import PyAudioPCM16Speaker
from pyaudio import PyAudio, paInt16
from io import BytesIO
from ghostos_common.helpers import Timeleft
import time
import wave

if __name__ == '__main__':

    listener = PyAudioPCM16Listener(
        sample_rate=44100,
        output_rate=24000,
    )
    ticker = Timeleft(0)

    heard = BytesIO()


    def write(d: bytes):
        heard.write(d)


    print("start listening, %f" % ticker.passed())
    with listener.listen(write):
        timeleft = Timeleft(3)
        print("listening real started, %f" % ticker.passed())
        while timeleft.alive():
            time.sleep(0.1)
    print("end listening, %f" % ticker.passed())

    heard.seek(0)
    print("test raw speaking, %f" % ticker.passed())
    stream = PyAudio().open(
        format=paInt16,
        channels=1,
        rate=24000,
        output=True,
    )
    stream.write(heard.getvalue())
    stream.close()
    print("end test raw speaking, %f" % ticker.passed())

    heard.seek(0)


    def read() -> Union[bytes, None]:
        return heard.read(1024)


    speaker = PyAudioPCM16Speaker(input_rate=24000, output_rate=44100)
    print("start speaking, %f" % ticker.passed())
    with speaker.speak(read) as speaking:
        speaking.wait()

    print("end speaking, %f" % ticker.passed())

    buffer = BytesIO()
    with wave.open(buffer, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(24000)
        f.writeframes(heard.getvalue())

    with open("test.wav", "wb") as f:
        f.write(buffer.getvalue())
