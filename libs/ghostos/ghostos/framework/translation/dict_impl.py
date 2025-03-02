from typing import Dict, List, Optional, Iterable
from abc import ABC, abstractmethod
from ghostos.contracts.translation import Translator, Translation, DomainTranslator, TransItem
from ghostos.contracts.storage import FileStorage
from ghostos.contracts.workspace import Workspace
from ghostos_container import Provider, Container, INSTANCE
from ghostos_common.helpers import yaml_pretty_dump, generate_import_path
from pydantic import BaseModel, Field
import yaml


class DomainTranslationData(BaseModel):
    domain: str = Field(description="the target domain")
    langs: List[str] = Field(default_factory=lambda: ["zh", "en"], description="the target langs")
    default_lang: str = "en"
    items: Dict[str, TransItem] = Field(default_factory=dict)


class BasicDomainTranslator(DomainTranslator, Translator, ABC):

    def __init__(self, data: DomainTranslationData):
        self.data = data

    def gettext(self, message: str, lang: str = "", **kwargs: str) -> str:
        item = self.get_item(message)
        if not lang:
            lang = self.default_lang
        return item.gettext(lang, **kwargs)

    def get_item(self, item_id: str) -> TransItem:
        if item_id not in self.data.items:
            self.data.items[item_id] = TransItem(id=item_id)
            self.save()
        item = self.data.items.get(item_id)
        return item

    def domain(self) -> str:
        return self.data.domain

    def langs(self) -> List[str]:
        return self.data.langs

    def default_lang(self) -> str:
        return self.data.default_lang

    def update(self, lang: str, text: str, value: str):
        item = self.data.items.get(text)
        if item is None:
            item = TransItem(id=text)
        item.translations[lang] = value
        self.data.items[item.id] = item
        self.save()


class YamlDomainTranslator(BasicDomainTranslator):

    def __init__(self, storage: FileStorage, domain: str):
        self.storage = storage
        filename = self.domain_yaml_name(domain)
        if not storage.exists(filename):
            data = DomainTranslationData(domain=domain)
            self.do_save(data)
        else:
            content = storage.get(filename)
            unmarshal = yaml.safe_load(content)
            data = DomainTranslationData(**unmarshal)
        super().__init__(data)

    def get_translator(self, lang: str = "") -> Translator:
        if lang and lang != self.data.default_lang:
            self.data.default_lang = lang
            self.save()
        return self

    @staticmethod
    def domain_yaml_name(domain: str) -> str:
        return f"{domain}.yml"

    def items(self) -> Iterable[TransItem]:
        yield from self.data.items.values()

    def save(self) -> None:
        self.do_save(self.data)

    def do_save(self, data_obj: DomainTranslationData) -> None:
        data = data_obj.model_dump()
        content = yaml_pretty_dump(data)
        content = f"# model is {generate_import_path(DomainTranslationData)} \n" + content
        filename = f"{data_obj.domain}.yml"
        self.storage.put(filename, content.encode())


class YamlAssetTranslation(Translation):

    def __init__(self, asset_storage: FileStorage):
        self.asset_storage = asset_storage
        self.domain_translators = {}

    def get_domain(self, domain: str) -> DomainTranslator:
        if domain not in self.domain_translators:
            translator = YamlDomainTranslator(self.asset_storage, domain)
            self.domain_translators[domain] = translator
        return self.domain_translators[domain]


class WorkspaceTranslationProvider(Provider[Translation]):

    def __init__(
            self,
            translation_dir: str = "translations",
    ):
        self.translation_dir = translation_dir

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[INSTANCE]:
        workspace = con.force_fetch(Workspace)
        storage = workspace.assets().sub_storage(self.translation_dir)
        return YamlAssetTranslation(storage)
