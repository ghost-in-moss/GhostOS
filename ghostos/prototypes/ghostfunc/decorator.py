import inspect
from typing import Callable, Optional, Dict
from ghostos_container import Container
from ghostos.prototypes.ghostfunc.driver import (
    GhostFuncDriver, GhostFuncCache, get_ghost_func_cache, save_ghost_func_cache,
)

__all__ = [
    'GhostFunc'
]

DECORATOR = Callable[[Callable], Callable]


class GhostFunc:
    def __init__(self, container: Container):
        self._container = container
        self._container.bootstrap()
        self._caches: Dict[str, GhostFuncCache] = {}
        self._compiled = set()

    def decorator(
            self,
            caching: bool = True,
            llm_api: str = "",
            saving: bool = True,
            filename: Optional[str] = None,
    ) -> DECORATOR:
        """
        produce a decorator to wrap a function.
        :param caching: if True, decorator will cache function body at first success run, and use it after.
        :param llm_api: the llm api that generating the function body.
        :param saving: if True, the thinking thread will save after each run.
        :param filename: if given, will save cache in the filename while saving is True, otherwise use default filename.
        :return: a decorator to wrap function.
        """

        def decorator(func: Callable) -> Callable:
            target_source = inspect.getsource(func)
            target_module = inspect.getmodule(func)
            target_modulename = target_module.__name__
            target_qualname = func.__qualname__
            target_filename = filename or target_module.__file__ + '.ghost_func.yml'
            cache = self._get_cache(target_modulename, target_filename)
            ghost_driver = GhostFuncDriver(
                container=self._container,
                cache=cache,
                target_module=target_modulename,
                target_qualname=target_qualname,
                target_file=target_filename,
                target_source=target_source,
                caching=caching,
                llm_api=llm_api,
            )

            def wrapped(*args, **kwargs):
                try:
                    result = ghost_driver.execute(list(args), kwargs)
                    # 只有 saving 时才保存.
                    if saving:
                        self._save_cache(cache)
                    return result
                finally:
                    ghost_driver.destroy()

            return wrapped

        return decorator

    def _get_cache(self, modulename: str, filename: str) -> GhostFuncCache:
        if filename in self._caches:
            return self._caches[filename]
        cache = get_ghost_func_cache(modulename, filename)
        self._caches[filename] = cache
        return cache

    def _save_cache(self, cache: GhostFuncCache):
        save_ghost_func_cache(cache)
