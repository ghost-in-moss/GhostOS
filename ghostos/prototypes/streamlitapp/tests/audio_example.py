import streamlit as st
from threading import Thread
from io import BytesIO, BufferedReader
from os import path
from pyaudio import PyAudio, paInt16

pyaudio = PyAudio()
import time

if "run" not in st.session_state:
    st.session_state["run"] = 0
st.session_state["run"] += 1
st.write(st.session_state["run"])


def write_audio_to_bytes(io_in: BytesIO, filename: str):
    with open(filename, "wb+") as fl:
        while True:
            r = io_in.read(1024)
            if not r:
                break
            fl.write(r)
            time.sleep(0.01)


t = None
io_output = None
if audio := st.audio_input("Audio file"):
    st.write(audio)
    st.write(len(audio.getvalue()))
    io_input = BytesIO(audio.getvalue())
    io_output = path.abspath("test.wav")

    t = Thread(target=write_audio_to_bytes, args=(io_input, io_output))
    t.start()
    time.sleep(0.1)

if io_output is not None:
    st.write("output start")
    now = time.time()
    with open(io_output, "rb+") as f:
        stream = pyaudio.open(
            format=paInt16,
            channels=1,
            rate=44100,
            output=True,
        )
        while True:
            got = f.read(1024)
            if not got:
                break
            stream.write(got)
        stream.stop_stream()
        stream.close()
    end = time.time()
    st.write(round(end - now, 2))
    st.write("output end")

if t is not None:
    t.join()
