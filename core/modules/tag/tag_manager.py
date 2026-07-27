"""
TagManager — CLI 兼容 shim（委托 ``Tag``）。

MIGRATED → ``core.modules.tag.tag.Tag``

新代码请::

    from core.modules.tag import Tag
    Tag().execute(scenario_name=...)
"""

from __future__ import annotations

from core.modules.tag.tag import Tag


class TagManager(Tag):
    """CLI / run_tag 兼容名；行为与 ``Tag`` 相同。"""

    def refresh_scenario(self) -> None:
        self.refresh()

    @property
    def scenario_cache(self) -> dict:
        """旧字段兼容：路径 → 摘要。"""
        return {
            tag_id: {
                "tag_key": tag_id,
                "key": info.key,
                "settings": info.settings,
                "hooks_module_path": info.hooks_module_path,
                "hooks_class_name": info.hooks_class_name,
            }
            for tag_id, info in self._by_id.items()
        }


__all__ = ["TagManager"]
