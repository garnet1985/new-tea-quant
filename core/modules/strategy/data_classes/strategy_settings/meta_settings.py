#!/usr/bin/env python3
"""
策略 Meta 设置（与 ``settings_example`` 第 1、2 节对齐）

职责：
- 仅承载 **name / description / core / is_enabled**
- 提供 ``apply_defaults`` / ``validate()`` / ``to_dict()``（``SettingsBase``）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .settings_base import SettingsBase, ValidationReport


@dataclass
class StrategyMetaSettings(SettingsBase):
    """
    策略元信息（与 userspace 策略 ``settings`` 字典中的顶层字段对应）。

    - ``name``：策略唯一名（目录名、日志）
    - ``description``：说明文案
    - ``core``：策略私有参数字典，缺省为 ``{}``
    - ``is_enabled``：是否参与 scan/simulate 等调度
    """

    name: str
    description: str
    core: Dict[str, Any]
    is_enabled: bool = False

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> StrategyMetaSettings:
        """从完整 ``settings`` 字典抽取 meta 字段（不写回 raw）。"""
        if not isinstance(raw, dict):
            raw = {}
        name = raw.get("name", "unknown")
        if name is not None and not isinstance(name, str):
            name = str(name)
        desc = raw.get("description", "")
        if desc is not None and not isinstance(desc, str):
            desc = str(desc)
        core = raw.get("core", {})
        if core is None:
            core = {}
        if not isinstance(core, dict):
            core = {}
        inst = cls(
            name=name or "unknown",
            description=desc or "",
            core=dict(core),
            is_enabled=bool(raw.get("is_enabled", False)),
        )
        inst.apply_defaults()
        return inst

    def apply_defaults(self) -> None:
        """类型归一与最小结构（与 ``from_raw`` 对齐，可重复调用）。"""
        self.name = str(self.name) if self.name is not None else "unknown"
        self.description = str(self.description) if self.description is not None else ""
        self.is_enabled = bool(self.is_enabled)
        if not isinstance(self.core, dict):
            self.core = {}
        else:
            self.core = dict(self.core)

    def validate(self) -> ValidationReport:
        """
        仅校验 meta 字段（Critical / Warning）。

        - name：非空且不能为 ``unknown``
        - core：必须为 dict（已在 apply_defaults 归一化，此处再确认）
        - description：空串仅 Warning（示例中建议填写）
        """
        self.apply_defaults()
        result = SettingsBase.new_validation()

        if not self.name or self.name.strip() == "" or self.name == "unknown":
            SettingsBase.add_critical(
                result,
                "name",
                "策略名称不能为空或为 'unknown'",
                suggested_fix='在 settings.py 中设置 "name": "your_strategy_name"（与目录名一致）',
            )

        if not isinstance(self.core, dict):
            SettingsBase.add_critical(
                result,
                "core",
                "core 必须为对象（dict）",
                suggested_fix='将 "core" 设为 {} 或包含策略参数的对象',
            )

        if not (self.description or "").strip():
            SettingsBase.add_warning(
                result,
                "description",
                "未填写 description，建议补充策略说明",
                suggested_fix='在 settings.py 中添加 "description": "..."',
            )

        return result

    def to_dict(self) -> Dict[str, Any]:
        """权威 meta 片段（深拷贝，不含用户 dict 引用）。"""
        return self.deep_copy_dict(
            {
                "name": self.name,
                "description": self.description,
                "core": self.core,
                "is_enabled": self.is_enabled,
            }
        )

    @property
    def strategy_name(self) -> str:
        """与历史命名 ``strategy_name`` 一致。"""
        return self.name
