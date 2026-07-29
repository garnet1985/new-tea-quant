"""``settings.data`` — base/required 数据声明。

消费者: TagSettings

相对 strategy.DataSettings：
- tag 的 base **允许非时序** data_key（路由 ``non_time_series`` 尚未实现）
- tag 的 base **允许纯 global 时序**（如 macro.gdp）
- 默认 ``min_required_records=0``
- 提供时间轴 / attach_to / ``base_route()`` 推导
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional

from core.modules.data_contract import ContractIssuer, ContractScope, ContractType

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class DataSettings(SettingsBase):
    """``settings.data`` — base + required；tag base 允许非时序。"""

    raw_settings: Dict[str, Any]
    _issuer: ClassVar[Optional[ContractIssuer]] = None

    @classmethod
    def contract_issuer(cls) -> ContractIssuer:
        if cls._issuer is None:
            cls._issuer = ContractIssuer()
            cls._issuer.discover()
        return cls._issuer

    @property
    def data(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "data")

    @property
    def base(self) -> Dict[str, Any]:
        block = self.data.get("base")
        return dict(block) if isinstance(block, dict) else {}

    @property
    def base_data_key(self) -> str:
        return self.normalize_base(self.base)["data_key"]

    @property
    def min_required_records(self) -> int:
        try:
            return max(int(self.data.get("min_required_records") or 0), 0)
        except (TypeError, ValueError):
            return 0

    @property
    def attach_to_data_key(self) -> str:
        return self.base_data_key

    @property
    def target_entity_type(self) -> str:
        return self.base_data_key.replace(".", "_")

    @property
    def tag_time_axis_based_on(self) -> str:
        configured = str(self.data.get("tag_time_axis_based_on") or "").strip()
        if configured:
            return configured
        return self.resolve_time_axis()

    def apply_defaults(self) -> None:
        if "data" not in self.raw_settings or not isinstance(self.raw_settings["data"], dict):
            self.raw_settings["data"] = {}
        data = self.raw_settings["data"]
        if "base" not in data or not isinstance(data.get("base"), dict):
            data["base"] = {
                "data_key": "stock.kline.daily",
                "params": {"adjust": "qfq"},
                "indicators": {},
            }
        base = data["base"]
        if not str(base.get("data_key") or "").strip():
            base["data_key"] = "stock.kline.daily"
        if "params" not in base or not isinstance(base.get("params"), dict):
            base["params"] = {}
        if "indicators" not in base or not isinstance(base.get("indicators"), dict):
            base["indicators"] = {}
        if "required" not in data or not isinstance(data.get("required"), list):
            data["required"] = []
        if "min_required_records" not in data:
            data["min_required_records"] = 0

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        self.apply_defaults()

        if not isinstance(self.raw_settings.get("data"), dict):
            SettingsBase.add_critical(
                report,
                "data",
                "data must be dict",
                suggested_fix="Set data to {}",
            )
            return report

        try:
            self.normalize_base(self.base)
        except ValueError as exc:
            SettingsBase.add_critical(report, "data.base", str(exc))

        required = self.data.get("required")
        if required is not None and not isinstance(required, list):
            SettingsBase.add_critical(
                report,
                "data.required",
                "data.required must be list",
            )

        if report.is_valid:
            try:
                decls = self.issue_declarations()
                # userspace required 不应与 base 重复（issue_declarations 会静默去重）
                base_key = decls[0]["data_key"] if decls else ""
                extras = self.data.get("required") or []
                if isinstance(extras, list):
                    seen_extra = set()
                    for i, raw in enumerate(extras):
                        if not isinstance(raw, dict):
                            continue
                        key = str(raw.get("data_key") or "").strip()
                        if not key:
                            continue
                        if key == base_key or key in seen_extra:
                            SettingsBase.add_critical(
                                report,
                                f"data.required[{i}]",
                                f"duplicate data_key: {key}",
                            )
                        seen_extra.add(key)
                self._validate_declarations(decls)
                axis = self.resolve_time_axis()
                self.raw_settings["data"]["tag_time_axis_based_on"] = axis
                self._validate_time_axis(axis, decls)
            except ValueError as exc:
                SettingsBase.add_critical(report, "data", str(exc))

        return report

    @classmethod
    def normalize_indicators(cls, raw: Any) -> Dict[str, Any]:
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError("indicators 须为 dict")
        return deepcopy(raw)

    def normalize_base(self, block: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(block, dict):
            raise ValueError("data.base 须为 dict")
        data_key = str(block.get("data_key") or "").strip()
        if not data_key:
            raise ValueError("data.base 缺少 data_key")
        return {
            "data_key": data_key,
            "params": dict(block.get("params") or {}),
            "indicators": self.normalize_indicators(block.get("indicators")),
        }

    def normalize_declaration_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(item, dict):
            raise ValueError("data.required 条目须为 dict")
        data_key = str(item.get("data_key") or "").strip()
        if not data_key:
            raise ValueError("data.required 条目缺少 data_key")
        return {
            "data_key": data_key,
            "params": dict(item.get("params") or {}),
            "indicators": self.normalize_indicators(item.get("indicators")),
        }

    def issue_declarations(self) -> List[Dict[str, Any]]:
        """返回 [base] + required（去重后；兼容 to_dict 展开后再 from_dict）。"""
        decls: List[Dict[str, Any]] = [self.normalize_base(self.base)]
        seen = {decls[0]["data_key"]}
        for raw in self.data.get("required") or []:
            item = self.normalize_declaration_item(raw)
            data_key = item["data_key"]
            if data_key in seen:
                continue
            seen.add(data_key)
            decls.append(item)
        return decls

    def resolve_time_axis(self) -> str:
        """优先时序 base，否则 required 中第一个时序源。"""
        preferred = self.base_data_key
        if self.is_time_series(preferred):
            return preferred
        for item in self.issue_declarations():
            key = str(item.get("data_key") or "").strip()
            if key and self.is_time_series(key):
                return key
        return preferred

    @classmethod
    def declaration_meta(cls, data_key: str) -> Optional[Dict[str, Any]]:
        decl = cls.contract_issuer().get_declaration(str(data_key or "").strip())
        if not isinstance(decl, dict):
            return None
        meta = decl.get("meta")
        return meta if isinstance(meta, dict) else None

    @classmethod
    def declaration_data_key(cls, item: Optional[Dict[str, Any]]) -> str:
        if not isinstance(item, dict):
            return ""
        return str(item.get("data_key") or "").strip()

    @classmethod
    def is_time_series(cls, data_key: str) -> bool:
        meta = cls.declaration_meta(data_key)
        if not meta:
            return False
        return str(meta.get("type") or "").strip().lower() == ContractType.TIME_SERIES

    @classmethod
    def is_per_entity(cls, data_key: str) -> bool:
        meta = cls.declaration_meta(data_key)
        if not meta:
            return False
        return str(meta.get("scope") or "").strip().lower() == ContractScope.PER_ENTITY

    @classmethod
    def is_global(cls, data_key: str) -> bool:
        meta = cls.declaration_meta(data_key)
        if not meta:
            return False
        return str(meta.get("scope") or "").strip().lower() == ContractScope.GLOBAL

    @classmethod
    def is_non_time_series(cls, data_key: str) -> bool:
        meta = cls.declaration_meta(data_key)
        if not meta:
            return False
        return (
            str(meta.get("type") or "").strip().lower()
            == ContractType.NON_TIME_SERIES
        )

    def base_route(self) -> str:
        """由 ``data.base`` 推断执行路由：``per_entity`` | ``global`` | ``non_time_series``。

        优先级：非时序 base → ``non_time_series``；否则 global 时序 → ``global``；
        其余（含 per_entity 时序）→ ``per_entity``。
        """
        key = self.base_data_key
        if self.is_non_time_series(key):
            return "non_time_series"
        if self.is_global(key) and self.is_time_series(key):
            return "global"
        return "per_entity"

    def requires_execution_mode(self) -> bool:
        """仅 per_entity 时序需要 ``calculation.execution.mode``。"""
        return self.base_route() == "per_entity"

    def _validate_declarations(self, decls: List[Dict[str, Any]]) -> None:
        issuer = self.contract_issuer()
        for i, item in enumerate(decls):
            data_key = item["data_key"]
            decl = issuer.get_declaration(data_key)
            if not isinstance(decl, dict):
                label = "data.base" if i == 0 else f"data.required[{i - 1}]"
                raise ValueError(f"{label}.data_key 未注册: {data_key!r}")

    def _validate_time_axis(self, axis: str, decls: List[Dict[str, Any]]) -> None:
        # 非时序 base 路由另开；本阶段仍要求能解析出时序轴（global / per_entity）
        if self.base_route() == "non_time_series":
            raise ValueError(
                "data.base 为非时序：non_time_series 路由尚未实现；"
                "请使用时序 base，或将时序源放入 data.required 并改用时序 base"
            )
        keys = {str(d.get("data_key") or "") for d in decls}
        if axis not in keys:
            raise ValueError(
                f"data.tag_time_axis_based_on={axis!r} 不在 base/required 的 data_key 列表内"
            )
        if not self.is_time_series(axis):
            raise ValueError(
                f"data.tag_time_axis_based_on={axis!r} 必须指向时序数据源"
            )

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        out = deepcopy(self.data)
        out["tag_time_axis_based_on"] = self.tag_time_axis_based_on
        return out


__all__ = ["DataSettings"]
