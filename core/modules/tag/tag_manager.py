"""
Tag Manager — 兼容 CLI 的 Facade 入口。

MIGRATED 实现体 → ``core.modules.tag.core.tag.Tag``

本类保留 ``TagManager`` 名称供 ``CliApp`` / launcher 使用，内部委托 ``Tag``。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from core.modules.tag.core.tag import Tag


class TagManager:
    """Tag Manager（委托 ``Tag`` facade）。"""

    def __init__(
        self,
        is_verbose: bool = False,
        dispatch_overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._tag = Tag(
            is_verbose=is_verbose,
            dispatch_overrides=dispatch_overrides,
        )
        # 兼容旧测试 / 调用方读取的属性
        self.is_verbose = self._tag.is_verbose
        self.data_mgr = self._tag.data_mgr
        self.tag_data_service = self._tag.tag_data_service
        self._dispatch_overrides = self._tag._dispatch_overrides

    @property
    def scenario_cache(self) -> Dict[str, Any]:
        """旧字段兼容：路径 → 摘要。"""
        return {
            tag_id: {
                "tag_key": tag_id,
                "key": info.key,
                "settings": info.settings,
                "hooks_module_path": info.hooks_module_path,
                "hooks_class_name": info.hooks_class_name,
            }
            for tag_id, info in self._tag._by_id.items()
        }

    def refresh_scenario(self) -> None:
        self._tag.refresh()

    def execute(
        self,
        scenario_name: str | None = None,
        settings: Dict[str, Any] | None = None,
        *,
        tag_key: str | None = None,
        on_pipeline_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        dry_run: bool = False,
    ) -> Optional[Dict[str, Any]]:
        return self._tag.execute(
            scenario_name=scenario_name,
            settings=settings,
            tag_key=tag_key,
            on_pipeline_progress=on_pipeline_progress,
            dry_run=dry_run,
        )


__all__ = ["TagManager"]
