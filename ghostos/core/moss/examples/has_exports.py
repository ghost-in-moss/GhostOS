import inspect
from ghostos.core.moss.exports import Exporter


class Exports(Exporter):
    getsource = inspect.getsource
