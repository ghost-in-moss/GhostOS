from contextlib import redirect_stdout
import io


class BufferPrint:
    """
    print 方法的替代.
    """

    def __init__(self):
        self._buffer = io.StringIO()

    def print(self, *args, **kwargs):
        with self._buffer as buffer, redirect_stdout(buffer):
            print(*args, **kwargs)

    def buffer(self) -> str:
        return self._buffer.getvalue()
