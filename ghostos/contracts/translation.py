from typing import List, Iterable, Dict
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

__all__ = ["Translation", "Translator", "DomainTranslator", "TransItem"]

# deprecated: use gettext instead


class TransItem(BaseModel):
    id: str = Field(description="the target text")
    description: str = Field(default="", description="the description")
    translations: Dict[str, str] = Field(
        default_factory=dict,
        description="the translations from lang to value"
    )

    def gettext(self, lang: str, **kwargs: str) -> str:
        if lang in self.translations:
            template = self.translations[lang]
            return template.format(**kwargs)
        # fallback
        return self.id


class Translator(ABC):
    """
    for i18n or l10n translation
    """

    @abstractmethod
    def domain(self) -> str:
        pass

    @abstractmethod
    def default_lang(self) -> str:
        pass

    @abstractmethod
    def gettext(self, message: str, lang: str = "", **kwargs: str) -> str:
        pass


class DomainTranslator(ABC):
    @abstractmethod
    def domain(self) -> str:
        pass

    @abstractmethod
    def langs(self) -> List[str]:
        pass

    @abstractmethod
    def default_lang(self) -> str:
        pass

    @abstractmethod
    def get_translator(self, lang: str = "") -> Translator:
        pass

    @abstractmethod
    def update(self, lang: str, text: str, value: str):
        pass

    @abstractmethod
    def save(self) -> None:
        pass

    @abstractmethod
    def items(self) -> Iterable[TransItem]:
        pass


class Translation(ABC):
    """
    i18n or l10n translation, can update from user interface
    todo: use gettext
    """

    @abstractmethod
    def get_domain(self, domain: str) -> DomainTranslator:
        pass
