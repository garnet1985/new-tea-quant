"""TagDefinition — 运行时 / DB 层标签定义实体。

消费者: Scenario, engines, MetadataEnsureService

与 ``TagDefinitionItem``（settings 切片）的关系：
- settings 层只有 name / display_name / description
- 本类额外持有 id / scenario_id / 时间戳（ensure 后填入）

边界: 纯数据 + serde；不负责 DB IO 或 settings 校验
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Union

from core.modules.tag.core.engines.shared.tag_settings.tag_definition_settings import (
    TagDefinitionItem,
)


@dataclass
class TagDefinition:
    """运行时 tag 定义（对应旧 TagModel，无 DB ensure）。"""

    name: str
    display_name: str = ""
    description: str = ""
    id: Optional[int] = None
    scenario_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # userspace 原始条目（可选保留，便于引擎读扩展字段）
    settings: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_settings_item(
        cls,
        item: Union[TagDefinitionItem, Dict[str, Any]],
    ) -> "TagDefinition":
        """从 settings.tag_definitions[] 构建（尚未 ensure）。"""
        if isinstance(item, TagDefinitionItem):
            parsed = item
            raw = item.to_dict()
        else:
            parsed = TagDefinitionItem.from_dict(item)
            raw = dict(item)
        return cls(
            name=parsed.name,
            display_name=parsed.display_name or parsed.name,
            description=parsed.description,
            settings=deepcopy(raw),
        )

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "TagDefinition":
        """从 DB 行 / job payload / ``to_dict()`` 恢复。"""
        if not isinstance(raw, dict):
            raise ValueError("TagDefinition.from_dict 需要 dict")
        name = str(raw.get("name") or "").strip()
        if not name:
            raise ValueError("TagDefinition.name 必填")
        display = str(raw.get("display_name") or name).strip()
        description = str(raw.get("description") or "").strip()
        settings = raw.get("settings")
        if not isinstance(settings, dict):
            settings = {
                "name": name,
                "display_name": display,
                "description": description,
            }
        return cls(
            name=name,
            display_name=display,
            description=description,
            id=cls._optional_int(raw.get("id")),
            scenario_id=cls._optional_int(raw.get("scenario_id")),
            created_at=raw.get("created_at"),
            updated_at=raw.get("updated_at"),
            settings=deepcopy(settings),
        )

    def to_dict(self) -> Dict[str, Any]:
        """序列化为 job / DB 友好 dict。"""
        return {
            "id": self.id,
            "name": self.name,
            "scenario_id": self.scenario_id,
            "display_name": self.display_name or self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_settings_dict(self) -> Dict[str, Any]:
        """回写 userspace 形态（无 DB 字段）。"""
        if self.settings:
            out = deepcopy(self.settings)
            out["name"] = self.name
            out.setdefault("display_name", self.display_name or self.name)
            out.setdefault("description", self.description)
            return out
        return {
            "name": self.name,
            "display_name": self.display_name or self.name,
            "description": self.description,
        }

    @property
    def is_persisted(self) -> bool:
        return self.id is not None

    def apply_db_meta(self, meta: Dict[str, Any]) -> None:
        """用 DB 行覆盖持久化字段（供 ensure service 调用）。"""
        if not isinstance(meta, dict):
            raise ValueError("db meta 须为 dict")
        self.id = self._optional_int(meta.get("id"))
        if "scenario_id" in meta:
            self.scenario_id = self._optional_int(meta.get("scenario_id"))
        if meta.get("display_name") is not None:
            self.display_name = str(meta.get("display_name") or self.display_name)
        if meta.get("description") is not None:
            self.description = str(meta.get("description") or "")
        if "created_at" in meta:
            self.created_at = meta.get("created_at")
        if "updated_at" in meta:
            self.updated_at = meta.get("updated_at")

    def has_meta_diff(self, db_meta: Dict[str, Any]) -> bool:
        """与 DB 行比较展示字段是否变化。"""
        if not isinstance(db_meta, dict):
            return True
        if (self.display_name or self.name) != str(db_meta.get("display_name") or ""):
            return True
        if self.description != str(db_meta.get("description") or ""):
            return True
        return False

    @staticmethod
    def _optional_int(value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


__all__ = ["TagDefinition"]
