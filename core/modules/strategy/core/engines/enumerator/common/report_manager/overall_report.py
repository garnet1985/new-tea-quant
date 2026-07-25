"""跨 entity 枚举汇总：统计 + overall_report.json + CLI present。"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Dict, FrozenSet, List, Optional, TextIO, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    OVERALL_REPORT_FILE,
)
from core.modules.strategy.core.engines.enumerator.common.artifacts.runtime_env import (
    RuntimeEnv,
)
from core.modules.strategy.core.engines.shared.services.simulation_output import (
    GoalAchievementCsv,
    InvestmentRow,
    EntityInvestmentCsv,
)
from core.modules.strategy.core.engines.shared.data_class.investment import (
    InvestmentResult,
    Lifecycle,
)
from core.modules.strategy.core.helpers.statistics import StatisticsHelper

# overall「Goal 成交」不计这些退出腿（强制收口 / 到期，非目标止盈止损）
NON_GOAL_EXIT_REASONS: FrozenSet[str] = frozenset(
    {
        "simulate_end",
        "expired",
        "period_end",
        "max_holding",
    }
)

@dataclass
class EntitySummaryRow:
    """overall 报告中单 entity 摘要行。

    边界:
    - 负责: 持仓数/胜负/ROI 等聚合字段的序列化
    - 不负责: 从 CSV 扫描聚合（见 OverallReport.build）
    - 调用方: OverallReport
    """

    entity_id: str
    investment_count: int = 0
    completed_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    goal_count: int = 0
    avg_weighted_roi: float = 0.0
    avg_holding_days: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "investment_count": self.investment_count,
            "completed_count": self.completed_count,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "goal_count": self.goal_count,
            "avg_weighted_roi": self.avg_weighted_roi,
            "avg_holding_days": self.avg_holding_days,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "EntitySummaryRow":
        data = raw or {}
        return cls(
            entity_id=str(data.get("entity_id") or ""),
            investment_count=int(data.get("investment_count") or 0),
            completed_count=int(data.get("completed_count") or 0),
            win_count=int(data.get("win_count") or 0),
            loss_count=int(data.get("loss_count") or 0),
            goal_count=int(data.get("goal_count") or 0),
            avg_weighted_roi=float(data.get("avg_weighted_roi") or 0.0),
            avg_holding_days=float(data.get("avg_holding_days") or 0.0),
        )


@dataclass
class OverallSummary:
    """跨 entity 枚举汇总指标。

    边界:
    - 负责: 总数/触发率/胜率等汇总字段的序列化
    - 不负责: 扫描 CSV（见 OverallReport）
    - 调用方: OverallReport
    """

    total_entities: int = 0
    entities_with_investments: int = 0
    total_investments: int = 0
    completed_investments: int = 0
    unfinished_investments: int = 0
    win_count: int = 0
    loss_count: int = 0
    total_goals: int = 0
    avg_weighted_roi: float = 0.0
    avg_holding_days: float = 0.0
    trigger_ratio: float = 0.0
    completed_ratio: float = 0.0
    win_ratio: float = 0.0
    exit_reasons: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entities": self.total_entities,
            "entities_with_investments": self.entities_with_investments,
            "total_investments": self.total_investments,
            "completed_investments": self.completed_investments,
            "unfinished_investments": self.unfinished_investments,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "total_goals": self.total_goals,
            "avg_weighted_roi": self.avg_weighted_roi,
            "avg_holding_days": self.avg_holding_days,
            "trigger_ratio": self.trigger_ratio,
            "completed_ratio": self.completed_ratio,
            "win_ratio": self.win_ratio,
            "exit_reasons": dict(self.exit_reasons or {}),
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OverallSummary":
        data = raw or {}
        return cls(
            total_entities=int(data.get("total_entities") or 0),
            entities_with_investments=int(data.get("entities_with_investments") or 0),
            total_investments=int(data.get("total_investments") or 0),
            completed_investments=int(data.get("completed_investments") or 0),
            unfinished_investments=int(data.get("unfinished_investments") or 0),
            win_count=int(data.get("win_count") or 0),
            loss_count=int(data.get("loss_count") or 0),
            total_goals=int(data.get("total_goals") or 0),
            avg_weighted_roi=float(data.get("avg_weighted_roi") or 0.0),
            avg_holding_days=float(data.get("avg_holding_days") or 0.0),
            trigger_ratio=float(data.get("trigger_ratio") or 0.0),
            completed_ratio=float(data.get("completed_ratio") or 0.0),
            win_ratio=float(data.get("win_ratio") or 0.0),
            exit_reasons=dict(data.get("exit_reasons") or {}),
        )


@dataclass
class OverallReport:
    """跨 entity 业务汇总（从每股 CSV 聚合 → overall_report.json）。

    边界:
    - 负责: 扫描 investments CSV → summary/entity_rows；落盘与 present
    - 不负责: 写单股 CSV、performance.json
    - 调用方: OverallReportHandle
    """

    OVERALL_REPORT_FILE = OVERALL_REPORT_FILE

    strategy_key: str
    version_id: int
    summary: OverallSummary
    entity_rows: List[EntitySummaryRow] = field(default_factory=list)
    created_at: str = ""

    # ── 工厂 ──

    @classmethod
    def build(
        cls,
        output_dir: Path,
        *,
        strategy_key: str,
        version_id: int,
        total_entities: Optional[int] = None,
    ) -> "OverallReport":
        runtime = RuntimeEnv.load(output_dir)
        entity_ids_in_run = runtime.entity_ids
        total = total_entities if total_entities is not None else len(entity_ids_in_run)

        entity_rows: List[EntitySummaryRow] = []
        all_investments: List[InvestmentRow] = []
        total_goals = 0
        exit_reasons: Dict[str, int] = {}

        for entity_id in EntityInvestmentCsv.collect_entity_ids(output_dir):
            investments = EntityInvestmentCsv.load(output_dir, entity_id)
            goals = GoalAchievementCsv.load(output_dir, entity_id)
            goal_fill_count = sum(
                1 for g in goals.rows if OverallReport._is_goal_fill(g.reason, g.goal_name)
            )
            row = cls._summarize_entity(entity_id, investments.rows, goal_fill_count)
            entity_rows.append(row)
            all_investments.extend(investments.rows)
            total_goals += goal_fill_count
            for inv in investments.rows:
                if inv.lifecycle == Lifecycle.COMPLETE.value and inv.exit_reason:
                    key = inv.exit_reason
                    exit_reasons[key] = exit_reasons.get(key, 0) + 1

        summary = cls._summarize_all(
            total_entities=total,
            entity_rows=entity_rows,
            investments=all_investments,
            total_goals=total_goals,
            exit_reasons=exit_reasons,
        )
        return cls(
            strategy_key=strategy_key or runtime.strategy_key,
            version_id=int(version_id or runtime.version_id),
            summary=summary,
            entity_rows=sorted(entity_rows, key=lambda item: item.entity_id),
            created_at=datetime.now().isoformat(),
        )

    @classmethod
    def load(cls, output_dir: Path) -> "OverallReport":
        path = output_dir / cls.OVERALL_REPORT_FILE
        return cls.from_dict(cls._read_json(path))

    # ── 落盘 ──

    def save(self, output_dir: Path) -> Path:
        path = output_dir / self.OVERALL_REPORT_FILE
        return self._write_json(path, self.to_dict())

    # ── 展示 ──

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        summary = self.summary
        lines = [
            "",
            "── 枚举汇总 ──",
            f"策略: {self.strategy_key}  version: {self.version_id}",
            (
                f"实体: {summary.total_entities}  "
                f"有投资: {summary.entities_with_investments}  "
                f"触发率: {summary.trigger_ratio * 100:.1f}%"
            ),
            (
                f"投资: {summary.total_investments}  "
                f"完成: {summary.completed_investments}  "
                f"未完成: {summary.unfinished_investments}  "
                f"完成率: {summary.completed_ratio * 100:.1f}%"
            ),
            (
                f"胜负: win {summary.win_count} / loss {summary.loss_count}  "
                f"胜率: {summary.win_ratio * 100:.1f}%"
            ),
            (
                f"平均 ROI: {summary.avg_weighted_roi * 100:.2f}%  "
                f"平均持有: {summary.avg_holding_days:.1f} 天  "
                f"Goal 成交: {summary.total_goals}"
            ),
        ]
        if summary.exit_reasons:
            reasons = ", ".join(
                f"{name}={count}"
                for name, count in sorted(summary.exit_reasons.items())
            )
            lines.append(f"退出原因: {reasons}")

        top = sorted(
            self.entity_rows,
            key=lambda row: row.investment_count,
            reverse=True,
        )[:5]
        if top:
            lines.append("Top 实体 (按投资数):")
            for row in top:
                lines.append(
                    f"  {row.entity_id}: investments={row.investment_count} "
                    f"completed={row.completed_count} goals={row.goal_count}"
                )

        for line in lines:
            print(line, file=out, flush=True)

    # ── 序列化 ──

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_key": self.strategy_key,
            "version_id": self.version_id,
            "summary": self.summary.to_dict(),
            "entity_rows": [row.to_dict() for row in self.entity_rows],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OverallReport":
        data = raw or {}
        rows_raw = data.get("entity_rows") or []
        return cls(
            strategy_key=str(data.get("strategy_key") or ""),
            version_id=int(data.get("version_id") or 0),
            summary=OverallSummary.from_dict(data.get("summary") or {}),
            entity_rows=[
                EntitySummaryRow.from_dict(item)
                for item in rows_raw
                if isinstance(item, dict)
            ],
            created_at=str(data.get("created_at") or ""),
        )

    # ── private: 统计 ──

    @staticmethod
    def _is_goal_fill(reason: str, goal_name: str = "") -> bool:
        """止盈/止损等目标腿；排除 simulate_end / expired 等强制收口。"""
        r = str(reason or "").strip().lower()
        n = str(goal_name or "").strip().lower()
        if r in NON_GOAL_EXIT_REASONS or n in NON_GOAL_EXIT_REASONS:
            return False
        return bool(r or n)

    @staticmethod
    def _summarize_entity(
        entity_id: str,
        rows: List[InvestmentRow],
        goal_count: int,
    ) -> EntitySummaryRow:
        completed = [row for row in rows if row.lifecycle == Lifecycle.COMPLETE.value]
        wins = [row for row in completed if row.result == InvestmentResult.WIN.value]
        losses = [row for row in completed if row.result == InvestmentResult.LOSS.value]
        roi_values = [row.weighted_roi for row in completed if row.entry_price > 0]
        holding_values = [float(row.holding_days) for row in completed if row.holding_days > 0]
        return EntitySummaryRow(
            entity_id=entity_id,
            investment_count=len(rows),
            completed_count=len(completed),
            win_count=len(wins),
            loss_count=len(losses),
            goal_count=goal_count,
            avg_weighted_roi=StatisticsHelper.calculate_avg(roi_values),
            avg_holding_days=StatisticsHelper.calculate_avg(holding_values),
        )

    @staticmethod
    def _summarize_all(
        *,
        total_entities: int,
        entity_rows: List[EntitySummaryRow],
        investments: List[InvestmentRow],
        total_goals: int,
        exit_reasons: Dict[str, int],
    ) -> OverallSummary:
        completed = [
            row for row in investments if row.lifecycle == Lifecycle.COMPLETE.value
        ]
        wins = [row for row in completed if row.result == InvestmentResult.WIN.value]
        losses = [row for row in completed if row.result == InvestmentResult.LOSS.value]
        roi_values = [row.weighted_roi for row in completed if row.entry_price > 0]
        holding_values = [
            float(row.holding_days) for row in completed if row.holding_days > 0
        ]
        entities_with_investments = sum(1 for row in entity_rows if row.investment_count > 0)
        decided = len(wins) + len(losses)
        return OverallSummary(
            total_entities=max(0, int(total_entities)),
            entities_with_investments=entities_with_investments,
            total_investments=len(investments),
            completed_investments=len(completed),
            unfinished_investments=len(investments) - len(completed),
            win_count=len(wins),
            loss_count=len(losses),
            total_goals=total_goals,
            avg_weighted_roi=StatisticsHelper.calculate_avg(roi_values),
            avg_holding_days=StatisticsHelper.calculate_avg(holding_values),
            trigger_ratio=StatisticsHelper.calculate_trigger_ratio(
                entities_with_investments,
                max(0, int(total_entities)),
            ),
            completed_ratio=StatisticsHelper.calculate_completed_ratio(
                len(completed),
                len(investments),
            ),
            win_ratio=(len(wins) / decided) if decided > 0 else 0.0,
            exit_reasons=exit_reasons,
        )

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))


class OverallReportHandle:
    """ReportManager.overall 门面：跨 entity 汇总读写与展示。

    边界:
    - 负责: overall_report.json 构建/落盘/present
    - 不负责: 单股 CSV 写入
    - 调用方: ReportManager
    """

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager
        self._report: Optional[OverallReport] = None

    def build(self, *, total_entities: Optional[int] = None) -> "OverallReportHandle":
        self._report = OverallReport.build(
            self._manager.output_dir,
            strategy_key=self._manager.strategy_key,
            version_id=self._manager.version_id,
            total_entities=total_entities,
        )
        return self

    def save(self) -> Path:
        if self._report is None:
            self.build()
        assert self._report is not None
        return self._report.save(self._manager.output_dir)

    def load(self) -> Dict[str, Any]:
        return OverallReport.load(self._manager.output_dir).to_dict()

    def present(self, stream: Optional[TextIO] = None) -> None:
        OverallReport.load(self._manager.output_dir).present(stream=stream)


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.common.report_manager.report_manager import (
        ReportManager,
    )


__all__ = [
    "OverallReportHandle",
]
