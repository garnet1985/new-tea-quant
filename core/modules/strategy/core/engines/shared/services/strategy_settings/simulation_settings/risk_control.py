"""``simulation.risk_control`` — 主观风控设置 + 判定 API。

合并原 ``services/risk_control.RiskControl``：本类既是 settings section，
也直接提供 ``should_skip_enter`` / ``should_force_exit``。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple, Union

from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

_REASON_PREFIX = "stock_status:"


@dataclass(frozen=True)
class ForceExitDecision:
    """持仓风控强制退出决定。"""

    reason: str
    close_invest: bool = True
    exit_ratio: float = 1.0


@dataclass(frozen=True)
class ForceExitRule:
    """单条 ``force_exit_when`` 规则。"""

    status: str
    close_invest: bool = True
    exit_ratio: float = 1.0


@dataclass(frozen=True)
class StatusTagPolicy:
    """状态标签列表（``skip_enter_when``）。"""

    KNOWN_TAGS: ClassVar[frozenset] = frozenset({"st", "star_st"})

    tags: Tuple[str, ...] = ()

    @classmethod
    def from_raw(
        cls,
        raw: Any,
        *,
        field_path: str = "simulation.risk_control.skip_enter_when",
    ) -> "StatusTagPolicy":
        if raw is None:
            return cls(())
        if not isinstance(raw, list):
            raise ValueError(f"{field_path} 必须为 list")
        out: List[str] = []
        for idx, item in enumerate(raw):
            if isinstance(item, dict):
                tag = str(item.get("status") or item.get("name") or "").strip().lower()
            else:
                tag = str(item or "").strip().lower()
            if not tag:
                continue
            if tag not in cls.KNOWN_TAGS:
                raise ValueError(
                    f"{field_path}[{idx}] 非法: {item!r}；允许: {sorted(cls.KNOWN_TAGS)}"
                )
            if tag not in out:
                out.append(tag)
        return cls(tuple(out))

    def match_reason(self, status_tags: Sequence[str]) -> Optional[str]:
        if not self.tags:
            return None
        active = {
            str(tag).strip().lower()
            for tag in status_tags
            if str(tag).strip()
        }
        if not active:
            return None
        for tag in self.tags:
            if tag in active:
                return f"{_REASON_PREFIX}{tag}"
        return None

    def to_list(self) -> List[str]:
        return list(self.tags)


@dataclass(frozen=True)
class ForceExitWhenPolicy:
    """``force_exit_when``：字符串标签或带 ``close_invest`` / ``exit_ratio`` 的规则对象。"""

    KNOWN_TAGS: ClassVar[frozenset] = StatusTagPolicy.KNOWN_TAGS

    rules: Tuple[ForceExitRule, ...] = ()

    @classmethod
    def from_raw(
        cls,
        raw: Any,
        *,
        field_path: str = "simulation.risk_control.force_exit_when",
    ) -> "ForceExitWhenPolicy":
        if raw is None:
            return cls(())
        if not isinstance(raw, list):
            raise ValueError(f"{field_path} 必须为 list")
        out: List[ForceExitRule] = []
        seen: set = set()
        for idx, item in enumerate(raw):
            rule = cls._parse_item(item, field_path=f"{field_path}[{idx}]")
            if rule.status in seen:
                continue
            seen.add(rule.status)
            out.append(rule)
        return cls(tuple(out))

    @classmethod
    def _parse_item(cls, item: Any, *, field_path: str) -> ForceExitRule:
        if isinstance(item, dict):
            status = str(item.get("status") or item.get("name") or "").strip().lower()
            if not status:
                raise ValueError(f"{field_path} 缺少 status")
            if status not in cls.KNOWN_TAGS:
                raise ValueError(
                    f"{field_path} 非法 status: {status!r}；允许: {sorted(cls.KNOWN_TAGS)}"
                )
            close_invest = item.get("close_invest") is True
            raw_exit = item.get("exit_ratio", item.get("sell_ratio"))
            if close_invest:
                exit_ratio = 1.0
            elif raw_exit is not None and raw_exit != "":
                exit_ratio = float(raw_exit)
                if exit_ratio <= 0.0 or exit_ratio > 1.0:
                    raise ValueError(f"{field_path}.exit_ratio 须在 (0, 1]")
            else:
                # 仅写 {"status": "st"} → 默认全平
                close_invest = True
                exit_ratio = 1.0
            return ForceExitRule(
                status=status,
                close_invest=close_invest,
                exit_ratio=exit_ratio,
            )

        status = str(item or "").strip().lower()
        if not status:
            raise ValueError(f"{field_path} 标签不能为空")
        if status not in cls.KNOWN_TAGS:
            raise ValueError(
                f"{field_path} 非法: {item!r}；允许: {sorted(cls.KNOWN_TAGS)}"
            )
        return ForceExitRule(status=status, close_invest=True, exit_ratio=1.0)

    @property
    def tags(self) -> Tuple[str, ...]:
        return tuple(rule.status for rule in self.rules)

    def match_decision(
        self,
        status_tags: Sequence[str],
        *,
        already_triggered: Sequence[str] = (),
    ) -> Optional[ForceExitDecision]:
        if not self.rules:
            return None
        active = {
            str(tag).strip().lower()
            for tag in status_tags
            if str(tag).strip()
        }
        if not active:
            return None
        triggered = {
            str(t).strip().lower()
            for t in already_triggered
            if str(t).strip()
        }
        for rule in self.rules:
            if rule.status not in active:
                continue
            if rule.status in triggered:
                continue
            return ForceExitDecision(
                reason=f"{_REASON_PREFIX}{rule.status}",
                close_invest=bool(rule.close_invest),
                exit_ratio=float(rule.exit_ratio),
            )
        return None

    def to_list(self) -> List[Union[str, Dict[str, Any]]]:
        out: List[Union[str, Dict[str, Any]]] = []
        for rule in self.rules:
            if rule.close_invest and float(rule.exit_ratio) >= 1.0:
                out.append(rule.status)
            else:
                out.append(
                    {
                        "status": rule.status,
                        "close_invest": bool(rule.close_invest),
                        "exit_ratio": float(rule.exit_ratio),
                    }
                )
        return out


@dataclass
class RiskControl(SettingsBase):
    """``settings.simulation.risk_control`` + 判定 API。

    - ``should_skip_enter``：触发日状态 → 跳过下游模拟（枚举仍保留）
    - ``should_force_exit``：持仓强平（退市恒生效 + ``force_exit_when``）
    """

    raw_settings: Dict[str, Any]

    @property
    def simulation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "simulation")

    @property
    def risk_control(self) -> Dict[str, Any]:
        block = self.simulation.get("risk_control")
        return block if isinstance(block, dict) else {}

    @property
    def skip_enter_when(self) -> StatusTagPolicy:
        return StatusTagPolicy.from_raw(
            self.risk_control.get("skip_enter_when"),
            field_path="simulation.risk_control.skip_enter_when",
        )

    @property
    def force_exit_when(self) -> ForceExitWhenPolicy:
        return ForceExitWhenPolicy.from_raw(
            self.risk_control.get("force_exit_when"),
            field_path="simulation.risk_control.force_exit_when",
        )

    @classmethod
    def with_skip_enter(cls, tags: Sequence[str]) -> "RiskControl":
        """测试 / 轻量构造：仅配置 skip_enter_when。"""
        return cls(
            raw_settings={
                "simulation": {
                    "risk_control": {
                        "skip_enter_when": [str(t).strip().lower() for t in tags if str(t).strip()],
                        "force_exit_when": [],
                    }
                }
            }
        )

    def should_skip_enter(self, *, status_tags: Sequence[str]) -> Optional[str]:
        """命中 ``skip_enter_when`` 时返回 ``stock_status:<tag>``，否则 ``None``。"""
        return self.skip_enter_when.match_reason(status_tags)

    def should_force_exit(
        self,
        *,
        entity_id: str,
        trade_date: str,
        status_tags: Sequence[str] = (),
        already_triggered: Sequence[str] = (),
        stock_meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[ForceExitDecision]:
        """持仓期状态风控：退市恒生效，其次 ``force_exit_when``。"""
        _ = entity_id
        day = str(trade_date or "").strip()
        triggered = {
            str(t).strip().lower()
            for t in already_triggered
            if str(t).strip()
        }

        if self._is_delisted(stock_meta, day) and "delisted" not in triggered:
            return ForceExitDecision(
                reason=f"{_REASON_PREFIX}delisted",
                close_invest=True,
                exit_ratio=1.0,
            )

        return self.force_exit_when.match_decision(
            status_tags,
            already_triggered=already_triggered,
        )

    @staticmethod
    def _is_delisted(
        stock_meta: Optional[Dict[str, Any]],
        trade_date: str,
    ) -> bool:
        if not stock_meta or not trade_date:
            return False
        delist = str(
            stock_meta.get("delist_date")
            or stock_meta.get("delisted_date")
            or ""
        ).strip()
        if not delist:
            return False
        return trade_date >= delist

    def apply_defaults(self) -> None:
        sim = self.raw_settings.setdefault("simulation", {})
        if not isinstance(sim, dict):
            self.raw_settings["simulation"] = {}
            sim = self.raw_settings["simulation"]
        risk = sim.setdefault("risk_control", {})
        if not isinstance(risk, dict):
            sim["risk_control"] = {}
            risk = sim["risk_control"]
        if "skip_enter_when" not in risk or risk.get("skip_enter_when") is None:
            risk["skip_enter_when"] = []
        if "force_exit_when" not in risk or risk.get("force_exit_when") is None:
            risk["force_exit_when"] = []

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        risk_raw = self.simulation.get("risk_control")
        if risk_raw is not None and not isinstance(risk_raw, dict):
            SettingsBase.add_critical(
                report,
                "simulation.risk_control",
                "risk_control must be dict",
            )
            return report

        self.apply_defaults()
        try:
            StatusTagPolicy.from_raw(
                self.risk_control.get("skip_enter_when"),
                field_path="simulation.risk_control.skip_enter_when",
            )
        except ValueError as exc:
            SettingsBase.add_critical(
                report,
                "simulation.risk_control.skip_enter_when",
                str(exc),
                suggested_fix=f"Allowed tags: {sorted(StatusTagPolicy.KNOWN_TAGS)}",
            )
        try:
            ForceExitWhenPolicy.from_raw(
                self.risk_control.get("force_exit_when"),
                field_path="simulation.risk_control.force_exit_when",
            )
        except ValueError as exc:
            SettingsBase.add_critical(
                report,
                "simulation.risk_control.force_exit_when",
                str(exc),
                suggested_fix=(
                    f'["st"] or [{{"status":"st","close_invest":True}}]; '
                    f"allowed: {sorted(ForceExitWhenPolicy.KNOWN_TAGS)}"
                ),
            )
        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {
            "skip_enter_when": self.skip_enter_when.to_list(),
            "force_exit_when": self.force_exit_when.to_list(),
        }


__all__ = [
    "ForceExitDecision",
    "ForceExitRule",
    "ForceExitWhenPolicy",
    "RiskControl",
    "StatusTagPolicy",
]
