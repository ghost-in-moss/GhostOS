from typing import Dict, Optional
from abc import ABC, abstractmethod
from contextlib import redirect_stdout
from ghostos_common.prompter import POM
from io import StringIO


class Memo(POM, ABC):
    """
    a code based Memo that help an agent to remember things by variables.
    the best way to use memo:
    1. save a memo object if you need to remember.
    2. first create a memo object, set description of the key.
    3. if you want always see some from the memo objects, save a watching code (test before saving)
    """

    @abstractmethod
    def dump_context(self) -> str:
        """
        dump memo context into a string. include:
        1. memo object definitions in pattern `key`: (type) description
        2. the watching code
        3. the stdout executing the watching code
        """
        pass

    @abstractmethod
    def save(self, key: str, value: object, desc: str = None) -> None:
        """
        save a memo object
        :param key: follow the python variable name convention
        :param value: serializable value
        :param desc: description of the `key` if first created. less than 50 words.
        """
        pass

    @abstractmethod
    def get(self, key) -> Optional[object]:
        """
        get a memo object
        :return: None if not defined
        """
        pass

    @abstractmethod
    def remove(self, name: str) -> None:
        """
        remove a memo object
        :param name:
        :return:
        """
        pass

    @abstractmethod
    def values(self) -> Dict[str, object]:
        """
        :return: the saved values
        """
        pass

    def watch(self, _code: str, _save: bool = False) -> str:
        """
        watch output by code.
        :param _code: the code to eval with memo values as locals
        :param _save: if save the code for dump context
        :return: std output or error (error start with Error)
        """
        _values = self.values()

        def printer(**kwargs):
            _buffer = StringIO()
            with redirect_stdout(_buffer):
                eval(_code)
            return _buffer.getvalue()

        try:
            output = printer(**_values)
            if _save:
                self._save_watch_code(_code)
            return "Watched:" + output
        except Exception as e:
            return "Error:" + str(e)

    @abstractmethod
    def _save_watch_code(self, code: str):
        """
        save the watching code, used in dump context.
        """
        pass
