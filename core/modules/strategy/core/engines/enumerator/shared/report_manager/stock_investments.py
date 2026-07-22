"""每股枚举产物：stock_investments.csv / goal_achievements.csv（仅核心字段）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Sequence, Tuple, TYPE_CHECKING

from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_consts import (
    ReportPaths,
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
    - 不负责: 文件 IO（见 StockInvestments）
    - 调用方: StockInvestments / OverallReport

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

    @classmethod
    def from_payload(cls, raw: Dict[str, Any]) -> "InvestmentRow":
        entry = _RowCoerce.require_dict(raw, "entry")
        exit_info = _RowCoerce.require_dict(raw, "exit_info")
        holding = _RowCoerce.require_dict(raw, "holding")
        outcome = _RowCoerce.require_dict(raw, "outcome")
        lifecycle = _RowCoerce.require_non_empty_str(raw.get("lifecycle"), "lifecycle")
        exit_price = exit_info.get("exit_price")
        exit_price_raw = exit_info.get("exit_price_raw")
        return cls(
            investment_id=_RowCoerce.require_investment_id(raw),
            trigger_date=_RowCoerce.require_non_empty_str(raw.get("trigger_date"), "trigger_date"),
            trigger_price=_RowCoerce.as_float(raw.get("trigger_price")),
            trigger_price_raw=_RowCoerce.as_float(raw.get("trigger_price_raw")),
            entry_date=_RowCoerce.as_str(entry.get("entry_date")),
            entry_price=_RowCoerce.as_float(entry.get("entry_price")),
            entry_price_raw=_RowCoerce.as_float(entry.get("entry_price_raw")),
            exit_date=_RowCoerce.as_str(exit_info.get("exit_date")),
            exit_price=_RowCoerce.as_float(exit_price) if exit_price not in (None, "") else 0.0,
            exit_price_raw=(
                _RowCoerce.as_float(exit_price_raw) if exit_price_raw not in (None, "") else 0.0
            ),
            exit_reason=_RowCoerce.as_str(exit_info.get("exit_reason")),
            lifecycle=lifecycle,
            result=_RowCoerce.as_str(outcome.get("result")),
            weighted_roi=_RowCoerce.as_float(outcome.get("weighted_roi")),
            holding_days=_RowCoerce.as_int(holding.get("days")),
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
        )


@dataclass
class GoalAchievementRow:
    """单笔 goal 成交腿 → goal_achievements.csv 行。

    边界:
    - 负责: goal payload/CSV 行互转
    - 不负责: 文件 IO（见 GoalAchievements）
    - 调用方: GoalAchievements / OverallReport
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
class StockInvestments:
    """单只股票的全部 investment 记录 → ``{entity_id}_stock_investments.csv``。

    边界:
    - 负责: 从 investment dicts 构建行、读写 CSV
    - 不负责: overall 汇总
    - 调用方: InvestmentsReport
    """

    FILE_SUFFIX: ClassVar[str] = "_stock_investments.csv"
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
    )

    entity_id: str
    rows: List[InvestmentRow] = field(default_factory=list)

    @classmethod
    def build(cls, entity_id: str, investments: Sequence[Dict[str, Any]]) -> "StockInvestments":
        return cls(
            entity_id=str(entity_id or "").strip(),
            rows=[
                InvestmentRow.from_payload(dict(item))
                for item in investments
                if isinstance(item, dict)
            ],
        )

    @classmethod
    def load(cls, output_dir: Path, entity_id: str) -> "StockInvestments":
        path = cls.file_path(output_dir, entity_id)
        return cls(
            entity_id=str(entity_id or "").strip(),
            rows=[InvestmentRow.from_csv_row(row) for row in read_csv_to_dicts(path)],
        )

    @classmethod
    def file_path(cls, output_dir: Path, entity_id: str) -> Path:
        return ReportPaths.entities_dir(output_dir) / f"{str(entity_id or '').strip()}{cls.FILE_SUFFIX}"

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
        nested = cls._scan_entity_ids(ReportPaths.entities_dir(output_dir))
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
class GoalAchievements:
    """单只股票的全部 goal 成交腿 → ``{entity_id}_goal_achievements.csv``。

    边界:
    - 负责: 从 investment.goals 构建行、读写 CSV
    - 不负责: overall 汇总
    - 调用方: InvestmentsReport
    """

    FILE_SUFFIX: ClassVar[str] = "_goal_achievements.csv"
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
    def build(cls, entity_id: str, investments: Sequence[Dict[str, Any]]) -> "GoalAchievements":
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
    def load(cls, output_dir: Path, entity_id: str) -> "GoalAchievements":
        path = cls.file_path(output_dir, entity_id)
        return cls(
            entity_id=str(entity_id or "").strip(),
            rows=[GoalAchievementRow.from_csv_row(row) for row in read_csv_to_dicts(path)],
        )

    @classmethod
    def file_path(cls, output_dir: Path, entity_id: str) -> Path:
        return ReportPaths.entities_dir(output_dir) / f"{str(entity_id or '').strip()}{cls.FILE_SUFFIX}"

    def save(self, output_dir: Path, *, append: bool = False) -> Path:
        path = self.file_path(output_dir, self.entity_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [row.to_csv_row() for row in self.rows]
        if append and path.is_file():
            existing = read_csv_to_dicts(path)
            rows = existing + rows
        write_dicts_to_csv(path, rows, preferred_order=list(self.COLUMNS))
        return path


class InvestmentsReport:
    """ReportManager.investments 门面：每股 CSV 追加写入。

    边界:
    - 负责: stock_investments / goal_achievements CSV
    - 不负责: overall 汇总、performance
    - 调用方: ReportManager（worker_buffer / flush）
    """

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager

    def append_entity(self, entity_id: str, investments: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        stock_investments = StockInvestments.build(entity_id, investments)
        goal_achievements = GoalAchievements.build(entity_id, investments)
        investment_files = 0
        goal_files = 0
        investment_rows = 0
        goal_rows = 0
        if stock_investments.rows:
            stock_investments.save(self._manager.output_dir, append=True)
            investment_files = 1
            investment_rows = len(stock_investments.rows)
        if goal_achievements.rows:
            goal_achievements.save(self._manager.output_dir, append=True)
            goal_files = 1
            goal_rows = len(goal_achievements.rows)
        return {
            "investment_files": investment_files,
            "goal_files": goal_files,
            "investment_rows": investment_rows,
            "goal_rows": goal_rows,
        }

    def flush_buffered(self, buffer: List[Dict[str, Any]]) -> Dict[str, int]:
        if not buffer:
            return {
                "written_files": 0,
                "opportunities_count": 0,
                "target_files": 0,
                "investment_files": 0,
                "goal_files": 0,
                "goal_rows_count": 0,
            }

        grouped = self._group_by_entity(buffer)
        investment_files = 0
        goal_files = 0
        investment_rows_count = 0
        goal_rows_count = 0

        for entity_id, investments in grouped.items():
            stats = self.append_entity(entity_id, investments)
            investment_files += stats["investment_files"]
            goal_files += stats["goal_files"]
            investment_rows_count += stats["investment_rows"]
            goal_rows_count += stats["goal_rows"]

        return {
            "written_files": investment_files,
            "opportunities_count": investment_rows_count,
            "target_files": goal_files,
            "investment_files": investment_files,
            "goal_files": goal_files,
            "goal_rows_count": goal_rows_count,
        }

    @staticmethod
    def _group_by_entity(buffer: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for entry in buffer:
            entity_id = str(entry.get("entity_id") or "").strip()
            if not entity_id:
                continue
            investment = entry.get("opportunity")
            if not isinstance(investment, dict):
                continue
            grouped.setdefault(entity_id, []).append(dict(investment))
        return grouped


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_manager import (
        ReportManager,
    )


__all__ = [
    "InvestmentsReport",
]
