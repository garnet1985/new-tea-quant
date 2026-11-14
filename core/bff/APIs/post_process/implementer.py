"""Post-process catalog implementer。"""

from __future__ import annotations

from typing import Any, Dict, List


class PostProcessImplementer:
    def __init__(self) -> None:
        self._Catalog = None

    def lazy_load(self) -> "PostProcessImplementer":
        if self._Catalog is None:
            from core.bff.APIs.post_process.helpers.catalog import PostProcessCatalog

            self._Catalog = PostProcessCatalog
        return self

    def list_adapters(self) -> List[Dict[str, Any]]:
        assert self._Catalog is not None
        return self._Catalog.list_adapters()

    def list_processors(self) -> List[Dict[str, Any]]:
        assert self._Catalog is not None
        return self._Catalog.list_processors()

    def set_enabled(self, key: str, enabled: bool) -> Dict[str, Any]:
        assert self._Catalog is not None
        return self._Catalog.set_enabled(key, enabled)

    def update_adapters(self, key: str, adapters: Dict[str, Any]) -> Dict[str, Any]:
        assert self._Catalog is not None
        return self._Catalog.update_adapters(key, adapters)


impl = PostProcessImplementer()
