from ghostiss.core.session.threads import Threads
from ghostiss.contracts.storage import Storage


class StorageThreads(Threads):

    def __init__(
            self, *,
            storage: Storage,
            relative_path: str = "threads",
    ):
        self._relative_path = relative_path
        self._storage = storage.sub_storage(relative_path)
