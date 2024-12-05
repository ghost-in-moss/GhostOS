from ghostos.framework.audio.pyaudio_io.listener import PyAudioListener
from ghostos.framework.audio.pyaudio_io.speaker import PyAudioSpeaker
from pyaudio import PyAudio, paInt16
from io import BytesIO
from ghostos.helpers import Timeleft

if __name__ == '__main__':

    listener = PyAudioListener()
    speaker = PyAudioSpeaker()
    ticker = Timeleft(0)

    hearing = BytesIO()
    print("start listening, %f" % ticker.passed())
    with listener:
        timeleft = Timeleft(3)
        while timeleft.alive():
            data = listener.hearing()
            if data is not None:
                hearing.write(data)
        heard = listener.flush()
    print("end listening, %f" % ticker.passed())
    assert heard is not None
    print("heard data: %d", len(heard))

    print("test raw outputting, %f" % ticker.passed())
    stream = PyAudio().open(
        format=paInt16,
        channels=1,
        rate=44100,
        output=True,
    )
    stream.write(heard)
    stream.stop_stream()
    stream.close()
    print("end raw outputting, %f" % ticker.passed())

    # print("start speaking buffer, %f" % ticker.passed())
    # with speaker:
    #     while data := hearing.read(1024):
    #         speaker.speak(data)
    # print("end speaking buffer, %f" % ticker.passed())

    print("start speaking flushed")
    with speaker:
        speaker.speak(heard)

    print("end speaking flushed")
