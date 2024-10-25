from __future__ import annotations
import time
import socks
from typing import Union

import websockets
import json
import logging
from websockets.sync.client import connect as ws_connect, ClientConnection
from threading import Thread
from queue import Queue, Empty
from pydantic import BaseModel, Field
from ghostos.contracts.logger import LoggerItf


# 拆一个 base model 方便未来做成表单.
class OpenAIWebsocketsConf(BaseModel):
    token: str = Field()
    uri: str = Field("wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01")
    close_check: float = Field(
        default=0.5,
        description="check if the connection is still going while sending event to server",
    )


class OpenAIWSConnection:
    """

    """

    def __init__(
            self,
            conf: OpenAIWebsocketsConf,
            recv_from_server: Queue,
            *,
            sock=None,
            logger: LoggerItf = None,
    ):
        """

        :param conf:
        :param recv_from_server:
        :param sock:
        :param logger:
        """
        self._running = False
        self._stopped = False
        self._send_queue = Queue()
        self._ws = None
        self._logger = logger if logger else logging.getLogger()
        self._conf = conf
        self._main_thread = Thread(target=self._connect, args=(recv_from_server, sock))
        self._main_thread.start()

    def send(self, event: Union[dict, None]) -> None:
        self._send_queue.put(event)

    def close(self):
        if self._stopped:
            return
        self._stopped = True
        if self._ws is not None:
            self._ws.close()
            self._ws = None
        self._logger.info("[OpenAIWSConnection] stop the connection")

    def join(self):
        self._main_thread.join()

    def _connect(
            self,
            recv_queue: Queue,
            sock=None,
    ):
        with ws_connect(
                uri=self._conf.uri,
                additional_headers={
                    "Authorization": "Bearer " + self._conf.token,
                    "OpenAI-Beta": "realtime=v1",
                },
                sock=sock,
        ) as ws:
            self._logger.info("[OpenAIWSConnection] connected")
            self._ws = ws
            t1 = Thread(target=self._send_when_available, args=(ws,))
            t2 = Thread(target=self._recv_until_closed, args=(ws, recv_queue))
            t1.start()
            t2.start()
            self._logger.info("[OpenAIWSConnection] connection closed, recycle resources.")
            t1.join()
            t2.join()
        self._stopped = True
        # inform the connection is closed
        recv_queue.put(None)
        recv_queue.task_done()
        while not self._send_queue.empty():
            # seems not necessary
            self._send_queue.get_nowait()
        self._send_queue = None
        self._logger.info("[OpenAIWSConnection] connection fully closed")

    def _recv_until_closed(self, ws: ClientConnection, recv_queue: Queue):
        try:
            while not self._stopped:
                try:
                    data = ws.recv()
                    if not data:
                        self._logger.error(f"[OpenAIWSConnection] receive empty data: {data}")
                        return
                    if data:
                        self._logger.debug(f"[OpenAIWSConnection] receive data: {data}")
                        event = json.loads(data)
                        recv_queue.put(event)
                        self._logger.debug("[OpenAIWSConnection] send data as event: %s", event)
                except websockets.exceptions.ConnectionClosed:
                    if not self._stopped:
                        self._logger.error(f"[OpenAIWSConnection] receive while connection closed but not stopped")
                        raise
                    self._stopped = True
                    self._logger.info(f"[OpenAIWSConnection] receive while connection closed")
        finally:
            self.close()

    def _send_when_available(self, ws: ClientConnection):
        try:
            while not self._stopped:
                try:
                    # use timeout to check alive
                    event = self._send_queue.get(timeout=self._conf.close_check)
                except Empty:
                    time.sleep(self._conf.close_check)
                    continue
                except TimeoutError:
                    continue
                if event is None:
                    # if receive None from agent queue, means agent stop the connection.
                    self._stopped = True
                    self._logger.info(f"[OpenAIWSConnection] got none event which means connection shall close")
                    break
                try:
                    data = json.dumps(event)
                    ws.send(data)
                    self._logger.debug(f"[OpenAIWSConnection] send data to server: %s", data)
                except websockets.exceptions.ConnectionClosedOK:
                    break
        finally:
            self.close()


connect = OpenAIWSConnection

if __name__ == "__main__":
    import os
    from ghostos.helpers import Timeleft

    _on_recv = Queue()

    s = socks.socksocket()
    s.set_proxy(socks.SOCKS5, "localhost", 1080)
    s.connect(("api.openai.com", 443))
    socket = s

    _token = os.environ["OPENAI_API_KEY"]
    print("+++++ token", _token)
    _conf = OpenAIWebsocketsConf(token=_token)
    _connection = connect(
        _conf,
        _on_recv,
        sock=socket,
    )


    def output(q: Queue, left: Timeleft):
        while left.alive():
            try:
                data = q.get_nowait()
                print("+++++", data)
                if data is None:
                    break
            except Empty:
                time.sleep(0.2)
            print("+++++ timeleft", left.left())


    _left = Timeleft(10)
    output_t = Thread(target=output, args=(_on_recv, _left))
    output_t.start()
    output_t.join()
    _connection.close()
    _connection.join()
    print("done")
