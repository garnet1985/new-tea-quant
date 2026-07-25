"""枚举 version 投资 / goal CSV 内容模型（InvestmentCsv）。

消费者: enumerator, price_factor, portfolio
边界: 行模型 + 按 ArtifactPaths 读/写 CSV
不负责: version 目录 resolve / runtime 投影（见 EnumOutput / EnumSource）
说明: 不仅是 parser——enumerator 写盘与 P/O 读取共用同一契约
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    GOAL_ACHIEVEMENTS_SUFFIX,
    STOCK_INVESTMENTS_SUFFIX,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.paths import (
    ArtifactPaths,
)
from core.utils.io.csv_io import read_csv_to_dicts, write_dicts_to_csv


class _RowCoerce:
    """Investment / Goal CSV 行字段强制转换。

    边界:
    - 负责: str/float/int 与必填字段校验
    - 不负责: 业务语义、文件 IO
    - 调用方: InvestmentRow / GoalAchievementRow（模块内私有）
    """

    @staticmethod
    def as_str(value: Any) -> str:
        if value is None:
            return ""
        if hasattr(value, "value"):
            return str(value.value)
        return str(value).strip()

    @staticmethod
    def as_float(value: Any, default: float = 0.0) -> float:
        if value is None or value == "":
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def as_int(value: Any, default: int = 0) -> int:
        if value is None or value == "":
            return default
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def as_optional_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def as_optional_bool(value: Any) -> Optional[bool]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ("true", "1", "yes"):
            return True
        if text in ("false", "0", "no"):
            return False
        return None

    @staticmethod
    def optional_bool_to_csv(value: Optional[bool]) -> str:
        if value is None:
            return ""
        return "1" if value else "0"

    @staticmethod
    def status_tags_from_raw(raw: Any) -> Tuple[str, ...]:
        if raw is None or raw == "":
            return ()
        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                return ()
            if text.startswith("["):
                try:
                    raw = json.loads(text)
                except json.JSONDecodeError:
                    return ()
            else:
                return (text,)
        if not isinstance(raw, (list, tuple)):
            return ()
        return tuple(str(x).strip() for x in raw if str(x).strip())

    @staticmethod
    def status_tags_to_csv(tags: Sequence[str]) -> str:
        cleaned = [str(t).strip() for t in tags if str(t).strip()]
        if not cleaned:
            return ""
        return json.dumps(cleaned, ensure_ascii=False)

    @staticmethod
    def require_non_empty_str(value: Any, field_name: str) -> str:
        if value is None:
            raise ValueError(f"{field_name} 不能为空")
        text = _RowCoerce.as_str(value)
        if not text:
            raise ValueError(f"{field_name} 不能为空")
        return text

    @staticmethod
    def require_dict(raw: Dict[str, Any], key: str) -> Dict[str, Any]:
        value = raw.get(key)
        if not isinstance(value, dict):
            raise ValueError(f"investment payload 缺少 {key}")
        return value

    @staticmethod
    def require_investment_id(raw: Dict[str, Any]) -> str:
        meta = _RowCoerce.require_dict(raw, "meta")
        return _RowCoerce.require_non_empty_str(
            meta.get("opportunity_id"), "meta.opportunity_id"
        )


@dataclass
class InvestmentRow:
    """单笔 investment → stock_investments.csv 行。

    边界:
    - 负责: payload/CSV 行互转（核心字段）
    - 不负责: 文件 IO（见 EntityInvestmentCsv）
    - 调用方: EntityInvestmentCsv / OverallReport

    价格字段：无后缀为前复权（qfq）；``*_raw`` 为不复权成交价（供 portfolio 定仓）。
    """

    investment_id: str = ""
    trigger_date: str = ""
    trigger_price: float = 0.0
    trigger_price_raw: float = 0.0
    entry_date: str = ""
    entry_price: float = 0.0
    entry_price_raw: float = 0.0
    exit_date: str = ""
    exit_price: float = 0.0
    exit_price_raw: float = 0.0
    exit_reason: str = ""
    lifecycle: str = ""
    result: str = ""
    weighted_roi: float = 0.0
    holding_days: int = 0
    enter_prev_close: Optional[float] = None
    enter_at_limit: Optional[bool] = None
    exit_prev_close: Optional[float] = None
    exit_at_limit: Optional[bool] = None
    stock_status_at_trigger: Tuple[str, ...] = ()
    enter_bar_volume: Optional[float] = None
    exit_bar_volume: Optional[float] = None

    @classmethod
    def from_payload(cls, raw: Dict[str, Any]) -> "InvestmentRow":
        entry = _RowCoerce.require_dict(raw, "entry")
        exit_info = _RowCoerce.require_dict(raw, "exit_info")
        holding = _RowCoerce.require_dict(raw, "holding")
        outcome = _RowCoerce.require_dict(raw, "outcome")
        lifecycle = _RowCoerce.require_non_empty_str(raw.get("lifecycle"), "lifecycle")
        exit_price = exit_info.get("price")
        exit_price_raw = exit_info.get("price_raw")
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        status_tags = _RowCoerce.status_tags_from_raw(
            metadata.get("stock_status_at_trigger")
        )
        if not status_tags:
            status_tags = _RowCoerce.status_tags_from_raw(
                raw.get("stock_status_at_trigger")
            )
        return cls(
            investment_id=_RowCoerce.require_investment_id(raw),
            trigger_date=_RowCoerce.require_non_empty_str(raw.get("trigger_date"), "trigger_date"),
            trigger_price=_RowCoerce.as_float(raw.get("trigger_price")),
            trigger_price_raw=_RowCoerce.as_float(raw.get("trigger_price_raw")),
            entry_date=_RowCoerce.as_str(entry.get("date")),
            entry_price=_RowCoerce.as_float(entry.get("price")),
            entry_price_raw=_RowCoerce.as_float(entry.get("price_raw")),
            exit_date=_RowCoerce.as_str(exit_info.get("date")),
            exit_price=_RowCoerce.as_float(exit_price) if exit_price not in (None, "") else 0.0,
            exit_price_raw=(
                _RowCoerce.as_float(exit_price_raw) if exit_price_raw not in (None, "") else 0.0
            ),
            exit_reason=_RowCoerce.as_str(exit_info.get("reason")),
            lifecycle=lifecycle,
            result=_RowCoerce.as_str(outcome.get("result")),
            weighted_roi=_RowCoerce.as_float(outcome.get("weighted_roi")),
            holding_days=_RowCoerce.as_int(holding.get("days")),
            enter_prev_close=_RowCoerce.as_optional_float(entry.get("prev_close")),
            enter_at_limit=_RowCoerce.as_optional_bool(entry.get("at_limit")),
            exit_prev_close=_RowCoerce.as_optional_float(exit_info.get("prev_close")),
            exit_at_limit=_RowCoerce.as_optional_bool(
                exit_info.get("at_limit")
            ),
            stock_status_at_trigger=status_tags,
            enter_bar_volume=_RowCoerce.as_optional_float(entry.get("bar_volume")),
            exit_bar_volume=_RowCoerce.as_optional_float(
                exit_info.get("bar_volume")
            ),
        )

    def to_csv_row(self) -> Dict[str, Any]:
        return {
            "investment_id": self.investment_id,
            "trigger_date": self.trigger_date,
            "trigger_price": self.trigger_price,
            "trigger_price_raw": self.trigger_price_raw,
            "entry_date": self.entry_date,
            "entry_price": self.entry_price,
            "entry_price_raw": self.entry_price_raw,
            "exit_date": self.exit_date,
            "exit_price": self.exit_price,
            "exit_price_raw": self.exit_price_raw,
            "exit_reason": self.exit_reason,
            "lifecycle": self.lifecycle,
            "result": self.result,
            "weighted_roi": self.weighted_roi,
            "holding_days": self.holding_days,
            "enter_prev_close": "" if self.enter_prev_close is None else self.enter_prev_close,
            "enter_at_limit": _RowCoerce.optional_bool_to_csv(self.enter_at_limit),
            "exit_prev_close": "" if self.exit_prev_close is None else self.exit_prev_close,
            "exit_at_limit": _RowCoerce.optional_bool_to_csv(self.exit_at_limit),
            "stock_status_at_trigger": _RowCoerce.status_tags_to_csv(
                self.stock_status_at_trigger
            ),
            "enter_bar_volume": "" if self.enter_bar_volume is None else self.enter_bar_volume,
            "exit_bar_volume": (
                "" if self.exit_bar_volume is None else self.exit_bar_volume
            ),
        }

    @classmethod
    def from_csv_row(cls, raw: Dict[str, Any]) -> "InvestmentRow":
        data = raw or {}
        return cls(
            investment_id=_RowCoerce.as_str(data.get("investment_id")),
            trigger_date=_RowCoerce.as_str(data.get("trigger_date")),
            trigger_price=_RowCoerce.as_float(data.get("trigger_price")),
            trigger_price_raw=_RowCoerce.as_float(data.get("trigger_price_raw")),
            entry_date=_RowCoerce.as_str(data.get("entry_date")),
            entry_price=_RowCoerce.as_float(data.get("entry_price")),
            entry_price_raw=_RowCoerce.as_float(data.get("entry_price_raw")),
            exit_date=_RowCoerce.as_str(data.get("exit_date")),
            exit_price=_RowCoerce.as_float(data.get("exit_price")),
            exit_price_raw=_RowCoerce.as_float(data.get("exit_price_raw")),
            exit_reason=_RowCoerce.as_str(data.get("exit_reason")),
            lifecycle=_RowCoerce.as_str(data.get("lifecycle")),
            result=_RowCoerce.as_str(data.get("result")),
            weighted_roi=_RowCoerce.as_float(data.get("weighted_roi")),
            holding_days=_RowCoerce.as_int(data.get("holding_days")),
            enter_prev_close=_RowCoerce.as_optional_float(data.get("enter_prev_close")),
            enter_at_limit=_RowCoerce.as_optional_bool(data.get("enter_at_limit")),
            exit_prev_close=_RowCoerce.as_optional_float(data.get("exit_prev_close")),
            exit_at_limit=_RowCoerce.as_optional_bool(data.get("exit_at_limit")),
            stock_status_at_trigger=_RowCoerce.status_tags_from_raw(
                data.get("stock_status_at_trigger")
            ),
            enter_bar_volume=_RowCoerce.as_optional_float(data.get("enter_bar_volume")),
            exit_bar_volume=_RowCoerce.as_optional_float(data.get("exit_bar_volume")),
        )

    def to_opportunity(self, entity_id: str) -> "Opportunity":
        """投影为 Opportunity，仅保留信号字段（屏蔽 entry/exit/result/roi 等）。

        供 portfolio ``on_pick_portfolio_member`` 使用。
        """
        from core.modules.strategy.core.engines.shared.data_class.opportunity import (
            Opportunity,
            OpportunityMeta,
            StockInfo,
        )

        eid = str(entity_id or "").strip()
        inv_id = str(self.investment_id or "").strip()
        trigger_date = str(self.trigger_date or "").strip()
        metadata: Dict[str, Any] = {}
        if self.stock_status_at_trigger:
            metadata[Opportunity.STATUS_AT_TRIGGER_KEY] = list(
                self.stock_status_at_trigger
            )
        return Opportunity(
            stock=StockInfo(id=eid),
            record_of_today={},
            trigger_date=trigger_date,
            trigger_price=float(self.trigger_price or 0.0),
            trigger_price_raw=float(self.trigger_price_raw or 0.0),
            meta=OpportunityMeta(
                opportunity_id=inv_id,
                scan_date=trigger_date,
            ),
            metadata=metadata,
        )


@dataclass
class GoalAchievementRow:
    """单笔 goal 成交腿 → goal_achievements.csv 行。

    边界:
    - 负责: goal payload/CSV 行互转
    - 不负责: 文件 IO（见 GoalAchievementCsv）
    - 调用方: GoalAchievementCsv / OverallReport
    """

    investment_id: str = ""
    goal_name: str = ""
    date: str = ""
    price: float = 0.0
    price_raw: float = 0.0
    exit_ratio: float = 0.0
    profit: float = 0.0
    weighted_profit: float = 0.0
    reason: str = ""
    roi: float = 0.0

    @classmethod
    def from_payload(cls, investment_id: str, raw: Dict[str, Any]) -> "GoalAchievementRow":
        if not isinstance(raw, dict):
            raise ValueError("goal payload 必须是 dict")
        return cls(
            investment_id=_RowCoerce.require_non_empty_str(investment_id, "investment_id"),
            goal_name=_RowCoerce.require_non_empty_str(raw.get("name"), "name"),
            date=_RowCoerce.require_non_empty_str(raw.get("date"), "date"),
            price=_RowCoerce.as_float(raw.get("price")),
            price_raw=_RowCoerce.as_float(raw.get("price_raw")),
            exit_ratio=_RowCoerce.as_float(raw.get("exit_ratio"), default=1.0),
            profit=_RowCoerce.as_float(raw.get("profit")),
            weighted_profit=_RowCoerce.as_float(raw.get("weighted_profit")),
            reason=_RowCoerce.require_non_empty_str(raw.get("reason"), "reason"),
            roi=_RowCoerce.as_float(raw.get("roi")),
        )

    def to_csv_row(self) -> Dict[str, Any]:
        return {
            "investment_id": self.investment_id,
            "goal_name": self.goal_name,
            "date": self.date,
            "price": self.price,
            "price_raw": self.price_raw,
            "exit_ratio": self.exit_ratio,
            "profit": self.profit,
            "weighted_profit": self.weighted_profit,
            "reason": self.reason,
            "roi": self.roi,
        }

    @classmethod
    def from_csv_row(cls, raw: Dict[str, Any]) -> "GoalAchievementRow":
        data = raw or {}
        return cls(
            investment_id=_RowCoerce.require_non_empty_str(data.get("investment_id"), "investment_id"),
            goal_name=_RowCoerce.require_non_empty_str(data.get("goal_name"), "goal_name"),
            date=_RowCoerce.require_non_empty_str(data.get("date"), "date"),
            price=_RowCoerce.as_float(data.get("price")),
            price_raw=_RowCoerce.as_float(data.get("price_raw")),
            exit_ratio=_RowCoerce.as_float(data.get("exit_ratio"), default=1.0),
            profit=_RowCoerce.as_float(data.get("profit")),
            weighted_profit=_RowCoerce.as_float(data.get("weighted_profit")),
            reason=_RowCoerce.require_non_empty_str(data.get("reason"), "reason"),
            roi=_RowCoerce.as_float(data.get("roi")),
        )


@dataclass
class EntityInvestmentCsv:
    """单只股票的全部 investment 记录 → ``{entity_id}_stock_investments.csv``。

    边界:
    - 负责: 从 investment dicts 构建行、读写 CSV
    - 不负责: overall 汇总
    - 调用方: enumerator InvestmentsReport / price_factor / portfolio
    """

    FILE_SUFFIX: ClassVar[str] = STOCK_INVESTMENTS_SUFFIX
    COLUMNS: ClassVar[Tuple[str, ...]] = (
        "investment_id",
        "trigger_date",
        "trigger_price",
        "trigger_price_raw",
        "entry_date",
        "entry_price",
        "entry_price_raw",
        "exit_date",
        "exit_price",
        "exit_price_raw",
        "exit_reason",
        "lifecycle",
        "result",
        "weighted_roi",
        "holding_days",
        "enter_prev_close",
        "enter_at_limit",
        "exit_prev_close",
        "exit_at_limit",
        "stock_status_at_trigger",
        "enter_bar_volume",
        "exit_bar_volume",
    )

    entity_id: str
    rows: List[InvestmentRow] = field(default_factory=list)

    @classmethod
    def build(cls, entity_id: str, investments: Sequence[Dict[str, Any]]) -> "EntityInvestmentCsv":
        return cls(
            entity_id=str(entity_id or "").strip(),
            rows=[
                InvestmentRow.from_payload(dict(item))
                for item in investments
                if isinstance(item, dict)
            ],
        )

    @classmethod
    def load(cls, output_dir: Path, entity_id: str) -> "EntityInvestmentCsv":
        path = cls.file_path(output_dir, entity_id)
        return cls(
            entity_id=str(entity_id or "").strip(),
            rows=[InvestmentRow.from_csv_row(row) for row in read_csv_to_dicts(path)],
        )

    @classmethod
    def file_path(cls, output_dir: Path, entity_id: str) -> Path:
        return ArtifactPaths.entities_dir(output_dir) / f"{str(entity_id or '').strip()}{cls.FILE_SUFFIX}"

    @classmethod
    def _scan_entity_ids(cls, directory: Path) -> List[str]:
        if not directory.is_dir():
            return []
        suffix = cls.FILE_SUFFIX
        return sorted(
            entry.name[: -len(suffix)]
            for entry in directory.iterdir()
            if entry.is_file() and entry.name.endswith(suffix)
        )

    @classmethod
    def collect_entity_ids(cls, output_dir: Path) -> List[str]:
        nested = cls._scan_entity_ids(ArtifactPaths.entities_dir(output_dir))
        if nested:
            return nested
        return cls._scan_entity_ids(output_dir)

    def save(self, output_dir: Path, *, append: bool = False) -> Path:
        path = self.file_path(output_dir, self.entity_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [row.to_csv_row() for row in self.rows]
        if append and path.is_file():
            existing = read_csv_to_dicts(path)
            rows = existing + rows
        write_dicts_to_csv(path, rows, preferred_order=list(self.COLUMNS))
        return path


@dataclass
class GoalAchievementCsv:
    """单只股票的全部 goal 成交腿 → ``{entity_id}_goal_achievements.csv``。

    边界:
    - 负责: 从 investment.goals 构建行、读写 CSV
    - 不负责: overall 汇总
    - 调用方: enumerator InvestmentsReport / price_factor / portfolio
    """

    FILE_SUFFIX: ClassVar[str] = GOAL_ACHIEVEMENTS_SUFFIX
    COLUMNS: ClassVar[Tuple[str, ...]] = (
        "investment_id",
        "goal_name",
        "date",
        "price",
        "price_raw",
        "exit_ratio",
        "profit",
        "weighted_profit",
        "reason",
        "roi",
    )

    entity_id: str
    rows: List[GoalAchievementRow] = field(default_factory=list)

    @classmethod
    def build(cls, entity_id: str, investments: Sequence[Dict[str, Any]]) -> "GoalAchievementCsv":
        rows: List[GoalAchievementRow] = []
        for investment in investments or []:
            if not isinstance(investment, dict):
                continue
            investment_id = _RowCoerce.require_investment_id(investment)
            goal_legs = investment.get("completed_goals")
            if goal_legs is None:
                goal_legs = []
            if not isinstance(goal_legs, list):
                raise ValueError("investment payload.completed_goals 必须是 list")
            for goal in goal_legs:
                if isinstance(goal, dict):
                    rows.append(GoalAchievementRow.from_payload(investment_id, goal))
        return cls(entity_id=str(entity_id or "").strip(), rows=rows)

    @classmethod
    def load(cls, output_dir: Path, entity_id: str) -> "GoalAchievementCsv":
        path = cls.file_path(output_dir, entity_id)
        return cls(
            entity_id=str(entity_id or "").strip(),
            rows=[GoalAchievementRow.from_csv_row(row) for row in read_csv_to_dicts(path)],
        )

    @classmethod
    def file_path(cls, output_dir: Path, entity_id: str) -> Path:
        return ArtifactPaths.entities_dir(output_dir) / f"{str(entity_id or '').strip()}{cls.FILE_SUFFIX}"

    def save(self, output_dir: Path, *, append: bool = False) -> Path:
        path = self.file_path(output_dir, self.entity_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [row.to_csv_row() for row in self.rows]
        if append and path.is_file():
            existing = read_csv_to_dicts(path)
            rows = existing + rows
        write_dicts_to_csv(path, rows, preferred_order=list(self.COLUMNS))
        return path


__all__ = [
    "InvestmentRow",
    "GoalAchievementRow",
    "EntityInvestmentCsv",
    "GoalAchievementCsv",
]
