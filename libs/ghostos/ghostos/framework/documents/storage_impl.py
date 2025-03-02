from typing import Iterable, List, Dict, Optional
from typing_extensions import Self

from ghostos_common.identifier import Identifier
from ghostos.contracts.storage import FileStorage
from ghostos.contracts.documents import Documents, DocumentRegistry
from ghostos_container import Provider, Container
from ghostos.contracts.configs import Configs, YamlConfig
from ghostos.contracts.workspace import Workspace
from pydantic import BaseModel, Field
from os.path import join


class StorageDocuments(Documents):

    def __init__(
            self,
            storage: FileStorage,
            *,
            domain: str,
            description: str,
            default_lang: str,
            ext: str,
            lang: str = "",
    ):
        self._domain = domain
        self._storage = storage
        self._description = description
        self._default_lang = default_lang
        self._ext = ext
        self._lang = lang or default_lang

    def with_lang(self, lang: str) -> Self:
        return StorageDocuments(
            self._storage,
            domain=self._domain,
            description=self._description,
            default_lang=self._default_lang,
            ext=self._ext,
            lang=lang,
        )

    def domain(self) -> str:
        return self._domain

    def directory(self) -> str:
        return self._storage.abspath()

    def description(self) -> str:
        return self._description

    def default_lang(self) -> str:
        return self._default_lang

    def langs(self) -> List[str]:
        # todo
        raise NotImplemented("todo")

    def make_path(self, locale: str, filename: str) -> str:
        return join(self.domain(), locale, filename + self._ext)

    def read(self, filename: str, lang: str = "") -> str:
        if not lang:
            lang = self._default_lang
        return self._read(lang, filename)

    def _read(self, locale: str, filename: str) -> str:
        path = self.make_path(locale, filename)
        if not self._storage.exists(path):
            path = self.make_path(self.default_lang(), filename)
        content = self._storage.get(path)
        return content.decode('utf-8')

    def iterate(self, depth: int = -1) -> Iterable[str]:
        raise NotImplemented("todo")


class StorageDocumentsRegistry(DocumentRegistry):

    def __init__(self):
        self._documents: Dict[str, Documents] = {}

    def get_domain(self, domain: str, lang: str = "") -> Documents:
        if domain in self._documents:
            docs = self._documents[domain]
            return docs.with_lang(lang)
        raise FileNotFoundError(f"documents domain not found: {domain}")

    def register(self, domain: Documents) -> None:
        self._documents[domain.domain()] = domain

    def list_domains(self) -> List[Identifier]:
        for domain in self._documents.values():
            yield domain.__identifier__()


class StorageDocumentsConfig(YamlConfig):
    relative_path = "documents_registry.yml"

    class DocConf(BaseModel):
        directory: str = Field(description="sub directory to the assets directory")
        domain: str = Field(description="Domain name")
        extension: str = Field(description="File extension")
        default_lang: str = Field(description="Default locale language name")
        description: str = Field(default="", description="Description")

    docs: List[DocConf] = Field(default_factory=list)


class ConfiguredDocumentRegistryProvider(Provider[DocumentRegistry]):

    def __init__(self, config_file: str = "documents_registry.yml"):
        self._config_file = config_file

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[DocumentRegistry]:
        class Conf(StorageDocumentsConfig):
            relative_path = self._config_file

        configs = con.force_fetch(Configs)
        conf = configs.get_or_create(Conf())

        workspace = con.force_fetch(Workspace)
        assets = workspace.assets()

        registry = StorageDocumentsRegistry()

        for c in conf.docs:
            doc = StorageDocuments(
                assets.sub_storage(c.directory),
                domain=c.domain,
                description=c.description,
                default_lang=c.default_lang,
                ext=c.extension,
            )
            registry.register(doc)
        return registry
