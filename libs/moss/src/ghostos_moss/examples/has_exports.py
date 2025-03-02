import inspect
from ghostos_moss.exports import Exporter


class Exports(Exporter):
    getsource = inspect.getsource
