#!/usr/bin/env python3
"""策略 Meta 设置（用户可见文档块，不含系统 name）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .settings_base import SettingsBase, ValidationReport

_KEYWORD_MAX_LEN = 64


def _coerce_meta_text(value: Any) -> str:
    """将 ``description`` 等用户文案规范为单行字符串（支持括号换行写的 tuple/list）。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        parts = [str(item).strip() for item in value if item is not None and str(item).strip()]
        return "".join(parts)
    return str(value).strip()


@dataclass
class StrategyDetailsSettings(SettingsBase):
    entry: List[str] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: Any) -> Optional["StrategyDetailsSettings"]:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            return None
        entry_raw = raw.get("entry")
        entry: List[str] = []
        if isinstance(entry_raw, list):
            for item in entry_raw:
                if item is None:
                    continue
                text = str(item).strip()
                if text:
                    entry.append(text)
        inst = cls(entry=entry)
        inst.apply_defaults()
        return inst

    def apply_defaults(self) -> None:
        self.entry = [str(x).strip() for x in (self.entry or []) if str(x).strip()]

    def validate(self) -> ValidationReport:
        self.apply_defaults()
        return SettingsBase.new_validation()

    def to_dict(self) -> Dict[str, Any]:
        if not self.entry:
            return {}
        return {"entry": list(self.entry)}


@dataclass
class StrategyMetaSettings(SettingsBase):
    display_name: str
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    details: Optional[StrategyDetailsSettings] = None

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "StrategyMetaSettings":
        block = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
        display_name = block.get("display_name", "")
        if display_name is not None and not isinstance(display_name, str):
            display_name = str(display_name)
        desc = _coerce_meta_text(block.get("description", ""))
        keywords_raw = block.get("keywords")
        keywords: List[str] = []
        if isinstance(keywords_raw, list):
            for item in keywords_raw:
                if item is None:
                    continue
                text = str(item).strip()
                if text:
                    keywords.append(text)
        details = StrategyDetailsSettings.from_raw(block.get("details"))
        inst = cls(
            display_name=display_name or "",
            description=desc or "",
            keywords=keywords,
            details=details,
        )
        inst.apply_defaults()
        return inst

    def apply_defaults(self) -> None:
        self.display_name = str(self.display_name) if self.display_name is not None else ""
        self.description = _coerce_meta_text(self.description)
        self.keywords = [str(x).strip() for x in (self.keywords or []) if str(x).strip()]
        if self.details is not None:
            self.details.apply_defaults()
            if not self.details.entry:
                self.details = None

    def validate(self) -> ValidationReport:
        self.apply_defaults()
        result = SettingsBase.new_validation()
        if not self.display_name.strip():
            SettingsBase.add_critical(
                result,
                "meta.display_name",
                "meta.display_name 不能为空",
                suggested_fix='在 settings.py 的 meta 中设置 "display_name": "策略展示名"',
            )
        if not (self.description or "").strip():
            SettingsBase.add_warning(
                result,
                "meta.description",
                "未填写 meta.description，建议补充策略说明",
            )
        for idx, kw in enumerate(self.keywords):
            if len(kw) > _KEYWORD_MAX_LEN:
                SettingsBase.add_warning(
                    result,
                    f"meta.keywords[{idx}]",
                    f"关键词过长（>{_KEYWORD_MAX_LEN} 字符），建议缩短",
                )
        if self.details is not None:
            merged = SettingsBase.merge_validation_results(result, self.details.validate())
            return merged
        return result

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        out: Dict[str, Any] = {
            "display_name": self.display_name,
            "description": self.description,
            "keywords": list(self.keywords),
        }
        if self.details is not None:
            details_dict = self.details.to_dict()
            if details_dict:
                out["details"] = details_dict
        return out


__all__ = ["StrategyDetailsSettings", "StrategyMetaSettings", "_coerce_meta_text"]
