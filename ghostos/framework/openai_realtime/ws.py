from __future__ import annotations
import time

import socks
from typing import Union, Optional

import urllib3.util
import websockets
import json
import logging
from websockets.sync.client import connect as ws_connect, ClientConnection
from ghostos.contracts.logger import LoggerItf, get_console_logger
from ghostos.helpers import get_openai_key
from pydantic import BaseModel, Field

__all__ = ['OpenAIWSConnection', 'OpenAIWebsocketsConf']


# 拆一个 base model 方便未来做成表单.
class OpenAIWebsocketsConf(BaseModel):
    api_key: str = Field(
        default_factory=get_openai_key,
        description="The OpenAI key used to authenticate with WebSockets.",
    )
    proxy: Optional[str] = Field(None, description="The proxy to connect to. only support socket v5 now")
    uri: str = Field("wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01")
    close_check: float = Field(
        default=0.5,
        description="check if the connection is still going while sending event to server",
    )


class OpenAIWSConnection:
    """
    websocket adapter, provides:
    1. connect config adaption
    2. event marshal and unmarshal
    3. exception catch
    """

    def __init__(
            self,
            conf: OpenAIWebsocketsConf,
            *,
            logger: LoggerItf = None,
    ):
        """
        :param conf:
        :param logger:
        """
        self._running = False
        self._closed = False
        self._logger = logger if logger else logging.getLogger()
        self._conf = conf
        sock = None
        if conf.proxy is not None:
            sock = self._create_socket(conf.proxy, conf.uri)
        # 同步创建 connection.
        self._ws = ws_connect(
            uri=self._conf.uri,
            additional_headers={
                "Authorization": "Bearer " + self._conf.api_key,
                "OpenAI-Beta": "realtime=v1",
            },
            sock=sock,
        )

    def _create_socket(self, proxy: str, uri: str):
        parsed = urllib3.util.parse_url(proxy)
        if parsed.scheme != "socks5":
            raise NotImplementedError(f"Only socks5 is supported, got {parsed.scheme}")
        host = parsed.hostname
        port = parsed.port
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, host, port)

        uri_parsed = urllib3.util.parse_url(uri)
        s.connect((uri_parsed.hostname, 443))
        return s

    def client(self) -> ClientConnection:
        if self._closed:
            raise RuntimeError("Connection was already stopped")
        return self._ws

    def send(self, event: dict) -> None:
        if self._closed:
            raise RuntimeError("Connection was already stopped")
        try:
            data = json.dumps(event)
            # last check
            if self._closed:
                return
            self._ws.send(data)
            self._logger.debug(f"[OpenAIWSConnection] send data to server: %s", data)
        except websockets.exceptions.ConnectionClosedOK:
            self.close()

    def recv(self, timeout: Union[float, None] = None, timeout_error: bool = False) -> Union[dict, None]:
        if self._closed:
            return None
        try:
            data = self._ws.recv(timeout=timeout)
            self._logger.debug(f"[OpenAIWSConnection] receive data")
            if not data:
                self._logger.error(f"[OpenAIWSConnection] receive empty data: {data}")
                return None
            if data:
                event = json.loads(data)
                self._logger.debug(f"[OpenAIWSConnection] receive event %s", event["type"])
                if not data:
                    return event
        except websockets.exceptions.ConnectionClosed:
            self.close()
            return None
        except TimeoutError:
            if timeout == 0:
                # return None as expected
                return None
            if timeout_error:
                raise
            self._logger.debug(f"[OpenAIWSConnection] receive data timeout, but expected")
            return None

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._ws is not None:
            self._ws.close()
            self._ws = None
        self._logger.debug("[OpenAIWSConnection] stop the connection")

    def closed(self) -> bool:
        return self._closed


connect = OpenAIWSConnection

# some local tests
if __name__ == "__main__":
    import os
    from ghostos.helpers import Timeleft

    _token = os.environ["OPENAI_API_KEY"]
    print("+++++ token", _token)
    _conf = OpenAIWebsocketsConf(token=_token)
    _conf.proxy = "socks5://127.0.0.1:1080"
    _c = connect(
        _conf,
        logger=get_console_logger(debug=True),
    )

    # test parallel actions
    _c.send({
        "type": "conversation.item.create",
        "previous_item_id": None,
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Hello, how are you?"
                }
            ]
        }
    })
    _c.send({
        "type": "response.create",
        "response": {},
    })

    left = Timeleft(10)
    while left.alive():
        _data = _c.recv(timeout=0)
        if _data:
            print("+++++", _data)
        time.sleep(0.2)
        print("+++++ timeleft", left.left())
    _c.close()

    print("done")