"""Scenario — 运行时 / DB 层 tag scenario 实体。

消费者: engines, MetadataEnsureService, Tag facade

与 ``TagSettings`` 的关系：
- settings 负责校验 / 默认值 / 展开
- Scenario 持有运行时身份字段 + nested TagDefinition + 展开后的 settings dict

边界: 纯数据 + serde；不负责 discovery、DB ensure 或全量 settings 校验
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.tag.core.data_class.tag_definition import TagDefinition
from core.modules.tag.core.enums import TagExecutionMode, TagUpdateMode

if TYPE_CHECKING:
    from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings


@dataclass
class Scenario:
    """运行时 scenario（对应旧 ScenarioModel，无 DB ensure）。"""

    # 系统路径 ID（directory tag_key），写入 DB scenario.name
    name: str
    # CLI alias（meta.key）
    key: str = ""
    display_name: str = ""
    description: str = ""
    is_enabled: bool = False
    recompute: bool = False
    is_dry_run: bool = False
    attach_to_data_key: str = ""
    target_entity_type: str = ""
    execution_mode: str = TagExecutionMode.ENTITY_BASED.value
    update_mode: str = TagUpdateMode.INCREMENTAL.value
    start_date: str = ""
    end_date: str = ""
    tag_definitions: List[TagDefinition] = field(default_factory=list)
    # TagSettings.to_dict() 展开结果，供引擎读全量配置
    settings: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_tag_settings(cls, tag_settings: "TagSettings") -> "Scenario":
        """从已（或将要）校验的 TagSettings 构建。"""
        tag_settings.apply_defaults()
        payload = tag_settings.to_dict()
        definitions = [
            TagDefinition.from_settings_item(item)
            for item in tag_settings.definition_items()
        ]
        name = tag_settings.name
        if not name:
            raise ValueError("Scenario.name（tag_key）不能为空")
        return cls(
            name=name,
            key=tag_settings.key or name,
            display_name=tag_settings.display_name or name,
            description=tag_settings.meta.description,
            is_enabled=tag_settings.is_enabled,
            recompute=tag_settings.recompute,
            is_dry_run=tag_settings.is_dry_run,
            attach_to_data_key=tag_settings.attach_to_data_key,
            target_entity_type=tag_settings.target_entity_type,
            execution_mode=tag_settings.execution_mode,
            update_mode=tag_settings.update_mode,
            start_date=tag_settings.start_date,
            end_date=tag_settings.end_date,
            tag_definitions=definitions,
            settings=payload,
        )

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Scenario":
        """从 DB 行 / 序列化 dict 恢复（可含 tag_definitions / settings）。"""
        if not isinstance(raw, dict):
            raise ValueError("Scenario.from_dict 需要 dict")
        name = str(raw.get("name") or "").strip()
        if not name:
            raise ValueError("Scenario.name 必填")

        settings = raw.get("settings")
        settings = deepcopy(settings) if isinstance(settings, dict) else {}

        defs_raw = raw.get("tag_definitions")
        if not isinstance(defs_raw, list):
            defs_raw = settings.get("tag_definitions") if isinstance(settings, dict) else []
        definitions: List[TagDefinition] = []
        if isinstance(defs_raw, list):
            for item in defs_raw:
                if isinstance(item, dict):
                    # job payload 可能已是运行时形态（含 id）
                    if "id" in item or "scenario_id" in item:
                        definitions.append(TagDefinition.from_dict(item))
                    else:
                        definitions.append(TagDefinition.from_settings_item(item))

        key = str(raw.get("key") or "").strip()
        if not key:
            meta = settings.get("meta") if isinstance(settings.get("meta"), dict) else {}
            key = str(meta.get("key") or name).strip()

        attach = str(
            raw.get("attach_to_data_key")
            or settings.get("attach_to_data_key")
            or ""
        ).strip()
        target = str(raw.get("target_entity_type") or "").strip()
        if not target:
            te = settings.get("target_entity")
            if isinstance(te, dict):
                target = str(te.get("type") or "").strip()

        execution_mode = str(
            raw.get("execution_mode") or settings.get("execution_mode") or ""
        ).strip().lower() or TagExecutionMode.ENTITY_BASED.value
        update_mode = str(
            raw.get("update_mode") or settings.get("update_mode") or ""
        ).strip().lower() or TagUpdateMode.INCREMENTAL.value

        display = str(raw.get("display_name") or "").strip()
        if not display:
            meta = settings.get("meta") if isinstance(settings.get("meta"), dict) else {}
            display = str(meta.get("display_name") or name).strip()

        description = str(raw.get("description") or "").strip()
        if not description:
            meta = settings.get("meta") if isinstance(settings.get("meta"), dict) else {}
            description = str(meta.get("description") or "").strip()

        return cls(
            name=name,
            key=key,
            display_name=display or name,
            description=description,
            is_enabled=bool(raw.get("is_enabled", settings.get("is_enabled", False))),
            recompute=bool(raw.get("recompute", settings.get("recompute", False))),
            attach_to_data_key=attach,
            target_entity_type=target,
            execution_mode=BacktestMode.normalize(execution_mode),
            update_mode=update_mode,
            start_date=str(raw.get("start_date") or settings.get("start_date") or "").strip(),
            end_date=str(raw.get("end_date") or settings.get("end_date") or "").strip(),
            tag_definitions=definitions,
            settings=settings,
            id=TagDefinition._optional_int(raw.get("id")),
            created_at=raw.get("created_at"),
            updated_at=raw.get("updated_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """DB / 列表展示用身份字段（不含完整 settings）。"""
        return {
            "id": self.id,
            "name": self.name,
            "key": self.key,
            "display_name": self.display_name or self.name,
            "description": self.description,
            "attach_to_data_key": self.attach_to_data_key,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_job_dict(self) -> Dict[str, Any]:
        """引擎 job 常用展开（含 tag_definitions 运行时 dict）。"""
        return {
            **self.to_dict(),
            "is_enabled": self.is_enabled,
            "recompute": self.recompute,
            "target_entity_type": self.target_entity_type,
            "execution_mode": self.execution_mode,
            "update_mode": self.effective_update_mode(),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "tag_definitions": [d.to_dict() for d in self.tag_definitions],
            "settings": deepcopy(self.settings),
        }

    @property
    def identifier(self) -> str:
        return self.name

    @property
    def is_persisted(self) -> bool:
        return self.id is not None

    @property
    def is_entity_based(self) -> bool:
        return self.execution_mode == BacktestMode.ENTITY_BASED.value

    @property
    def is_slice_based(self) -> bool:
        return self.execution_mode == BacktestMode.SLICE_BASED.value

    def definitions_by_name(self) -> Dict[str, TagDefinition]:
        return {d.name: d for d in self.tag_definitions}

    def effective_update_mode(self) -> str:
        if self.recompute:
            return TagUpdateMode.REFRESH.value
        return self.update_mode or TagUpdateMode.INCREMENTAL.value

    def apply_db_meta(self, meta: Dict[str, Any]) -> None:
        """用 DB 行覆盖持久化字段（供 ensure service 调用）。"""
        if not isinstance(meta, dict):
            raise ValueError("db meta 须为 dict")
        self.id = TagDefinition._optional_int(meta.get("id"))
        if meta.get("display_name") is not None:
            self.display_name = str(meta.get("display_name") or self.display_name)
        if meta.get("description") is not None:
            self.description = str(meta.get("description") or "")
        if meta.get("key") is not None:
            key = str(meta.get("key") or "").strip()
            if key:
                self.key = key
        if meta.get("attach_to_data_key") is not None:
            attach = str(meta.get("attach_to_data_key") or "").strip()
            if attach:
                self.attach_to_data_key = attach
        if "created_at" in meta:
            self.created_at = meta.get("created_at")
        if "updated_at" in meta:
            self.updated_at = meta.get("updated_at")

    def has_meta_diff(self, db_meta: Dict[str, Any]) -> bool:
        if not isinstance(db_meta, dict):
            return True
        if (self.display_name or self.name) != str(db_meta.get("display_name") or ""):
            return True
        if self.description != str(db_meta.get("description") or ""):
            return True
        want_key = str(self.key or self.name or "").strip()
        have_key = str(db_meta.get("key") or "").strip()
        if want_key != have_key:
            return True
        want_attach = str(self.attach_to_data_key or "").strip()
        have_attach = str(db_meta.get("attach_to_data_key") or "").strip()
        if want_attach != have_attach:
            return True
        return False


__all__ = ["Scenario"]
