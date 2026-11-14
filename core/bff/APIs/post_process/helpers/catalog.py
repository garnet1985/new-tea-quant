"""Post-process catalog DTO（薄封装 Facade 摘要）。"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.modules.post_process import PostProcess


class PostProcessCatalog:
    @staticmethod
    def list_adapters() -> List[Dict[str, Any]]:
        return PostProcess.list_adapter_summaries()

    @staticmethod
    def list_processors() -> List[Dict[str, Any]]:
        return PostProcess.list_post_processor_summaries()

    @staticmethod
    def set_enabled(key: str, enabled: bool) -> Dict[str, Any]:
        PostProcess.set_enabled(key, enabled)
        row = PostProcess.summarize_post_processor(key)
        if row is None:
            raise ValueError(f"PostProcessor 不存在: {key}")
        return row

    @staticmethod
    def update_adapters(key: str, adapters: Dict[str, Any]) -> Dict[str, Any]:
        PostProcess.update_post_processor_adapters(key, adapters)
        row = PostProcess.summarize_post_processor(key)
        if row is None:
            raise ValueError(f"PostProcessor 不存在: {key}")
        return row


__all__ = ["PostProcessCatalog"]
