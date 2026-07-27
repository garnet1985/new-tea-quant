"""用户钩子回调入参：TagContext 壳 + 嵌套只读块。

消费者: TagHooks, TagSliceJobExecutor

本文件:
- TagInfo / TagData: 只读 dataclass
- TagContext: tag + settings + data + custom（custom 为可写 dict）
  边界: 用户可见四块；引擎用 assemble / fill / with_data 组装
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple, TYPE_CHECKING

from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings

if TYPE_CHECKING:
    from core.modules.tag.core.data_class.tag_definition import TagDefinition


def _freeze_map(raw: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    return MappingProxyType(dict(raw or {}))


@dataclass(frozen=True)
class TagInfo:
    """Tag 身份（只读；CLI alias / 路径）。"""

    key: str
    path: str = ""


@dataclass(frozen=True)
class TagData:
    """运行数据（只读）。

    - ``calculate_tag``：``items`` 为单实体 DataKey→rows；带 ``entity_id`` / ``tag_definition``
    - ``on_calendar_asof``：``by_entity`` 为 entity_id→当日 payload；``calendar`` 为日历元数据
    """

    now: str = ""
    entity_list: Tuple[str, ...] = ()
    entity_id: str = ""
    entity_info: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    items: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    by_entity: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    calendar: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    tag_definition: Optional["TagDefinition"] = None

    @staticmethod
    def build(
        *,
        now: str = "",
        entity_list: Optional[List[str]] = None,
        entity_id: str = "",
        entity_info: Optional[Mapping[str, Any]] = None,
        items: Optional[Mapping[str, Any]] = None,
        by_entity: Optional[Mapping[str, Any]] = None,
        calendar: Optional[Mapping[str, Any]] = None,
        tag_definition: Optional["TagDefinition"] = None,
    ) -> "TagData":
        return TagData(
            now=str(now or "").strip(),
            entity_list=tuple(
                str(x).strip() for x in (entity_list or []) if str(x).strip()
            ),
            entity_id=str(entity_id or "").strip(),
            entity_info=_freeze_map(entity_info),
            items=_freeze_map(items),
            by_entity=_freeze_map(by_entity),
            calendar=_freeze_map(calendar),
            tag_definition=tag_definition,
        )


@dataclass
class TagContext:
    """钩子回调入参壳：只读块 + 唯一可写 ``custom``。"""

    tag: TagInfo
    settings: TagSettings
    data: TagData
    custom: Dict[str, Any] = field(default_factory=dict)
    _cached_settings_dict: Optional[Dict[str, Any]] = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    @property
    def base_data_key(self) -> str:
        return self.settings.data.base_data_key

    def effective_settings_dict(self) -> Dict[str, Any]:
        cached = self._cached_settings_dict
        if cached is None:
            cached = self.settings.to_dict()
            self._cached_settings_dict = cached
        return cached

    def with_data(self, data: TagData) -> "TagContext":
        ctx = TagContext(
            tag=self.tag,
            settings=self.settings,
            data=data,
            custom=self.custom,
        )
        ctx._cached_settings_dict = self._cached_settings_dict
        return ctx

    @classmethod
    def assemble(
        cls,
        *,
        tag_key: str,
        settings: TagSettings,
        entity_list: List[str],
        tag_path: str = "",
        entity_id: str = "",
        entity_info: Optional[Mapping[str, Any]] = None,
        custom: Optional[Dict[str, Any]] = None,
    ) -> "TagContext":
        """0→1：建立壳（尚无当日 items / by_entity）。"""
        return cls(
            tag=TagInfo(
                key=str(tag_key or "").strip(),
                path=str(tag_path or "").strip(),
            ),
            settings=settings,
            data=TagData.build(
                entity_list=entity_list,
                entity_id=entity_id,
                entity_info=entity_info,
            ),
            custom=dict(custom or {}),
        )

    @classmethod
    def fill(
        cls,
        base: "TagContext",
        *,
        now: str,
        items: Optional[Mapping[str, Any]] = None,
        by_entity: Optional[Mapping[str, Any]] = None,
        calendar: Optional[Mapping[str, Any]] = None,
        entity_id: Optional[str] = None,
        entity_info: Optional[Mapping[str, Any]] = None,
        tag_definition: Optional["TagDefinition"] = None,
    ) -> "TagContext":
        """基于 base 填当日只读 data（共享 custom）。"""
        if base is None:
            raise ValueError("TagContext.fill 要求非空 base")
        entity_list = list(base.data.entity_list)
        if not entity_list:
            raise ValueError("TagContext.fill 要求 base 已 assemble（含 entity_list）")
        return base.with_data(
            TagData.build(
                now=now,
                entity_list=entity_list,
                entity_id=base.data.entity_id if entity_id is None else entity_id,
                entity_info=(
                    base.data.entity_info if entity_info is None else entity_info
                ),
                items=items,
                by_entity=by_entity if by_entity is not None else base.data.by_entity,
                calendar=calendar if calendar is not None else base.data.calendar,
                tag_definition=(
                    base.data.tag_definition
                    if tag_definition is None
                    else tag_definition
                ),
            )
        )


__all__ = ["TagContext", "TagData", "TagInfo"]
