"""枚举报告 build 共用：扫描 entities JSON（CSV fallback DEPRECATED）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.modules.strategy.core.engines.enumerator.common.artifacts.runtime_env import (
    RuntimeEnv,
)
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResult,
    EnumResultsManager,
)
from core.modules.strategy.core.services.artifacts import EnumerateStore, InvestmentRow


@dataclass
class EnumCsvScan:
    """一次扫盘结果，供 OverallReport / EntityListReport 共用。

    优先读 ``entities/{id}.json``；无 JSON 时回退 CSV（DEPRECATED）。
    """

    total_entities: int
    investments_by_entity: Dict[str, List[InvestmentRow]] = field(default_factory=dict)
    strategy_key: str = ""
    strategy_path: str = ""
    version_id: int = 0
    execution_mode: str = ""
    backtest_period: Dict[str, str] = field(default_factory=dict)

    @property
    def all_investments(self) -> List[InvestmentRow]:
        rows: List[InvestmentRow] = []
        for part in self.investments_by_entity.values():
            rows.extend(part)
        return rows

    @classmethod
    def collect(
        cls,
        output_dir: Path,
        *,
        total_entities: Optional[int] = None,
        strategy_key: str = "",
        version_id: int = 0,
    ) -> "EnumCsvScan":
        runtime = RuntimeEnv.load(output_dir)
        entity_ids_in_run = list(runtime.entity_ids or [])
        total = (
            int(total_entities)
            if total_entities is not None
            else len(entity_ids_in_run)
        )
        period = runtime.period
        period_dict = {
            str(k): str(v or "")
            for k, v in dict(period.to_dict() or {}).items()
        }

        investments_by_entity = _load_investments_by_entity(output_dir)

        return cls(
            total_entities=max(0, total),
            investments_by_entity=investments_by_entity,
            strategy_key=str(strategy_key or runtime.strategy_key or ""),
            strategy_path=str(runtime.strategy_path or runtime.strategy_key or ""),
            version_id=int(version_id or runtime.version_id or 0),
            execution_mode=str(runtime.execution_mode or ""),
            backtest_period=period_dict,
        )


def _load_investments_by_entity(output_dir: Path) -> Dict[str, List[InvestmentRow]]:
    manager = EnumResultsManager.at(output_dir)
    json_ids = [
        entity_id
        for entity_id in manager.list_entities()
        if manager.entity_path(entity_id).is_file()
    ]
    if json_ids:
        return {
            entity_id: [
                _enum_result_to_investment_row(row)
                for row in manager.results(entity_id)
            ]
            for entity_id in json_ids
        }
    # DEPRECATED: CSV sidecar，待枚举报告改读 EnumResult 后删除
    store = EnumerateStore.at(output_dir)
    return {
        entity_id: list(rows)
        for entity_id, rows in store.load_all_investments().items()
    }


def _enum_result_to_investment_row(row: EnumResult) -> InvestmentRow:
    """报告层适配：OverallReport 仍吃 InvestmentRow，待其改读 EnumResult 后删除。"""
    return InvestmentRow(
        investment_id=row.investment_id,
        trigger_date=row.trigger_date,
        trigger_price=row.trigger_price,
        trigger_price_raw=row.trigger_price_raw,
        trigger_price_hfq=row.trigger_price_hfq,
        entry_date=row.entry_date,
        entry_price=row.entry_price,
        entry_price_raw=row.entry_price_raw,
        entry_price_hfq=row.entry_price_hfq,
        exit_date=row.exit_date,
        exit_price=row.exit_price,
        exit_price_raw=row.exit_price_raw,
        exit_price_hfq=row.exit_price_hfq,
        exit_reason=row.exit_reason,
        lifecycle=row.lifecycle,
        result=row.result,
        weighted_roi=row.weighted_roi,
        holding_days=row.holding_days,
        enter_prev_close=row.enter_prev_close,
        enter_at_limit=row.enter_at_limit,
        exit_prev_close=row.exit_prev_close,
        exit_at_limit=row.exit_at_limit,
        stock_status_at_trigger=row.stock_status_at_trigger,
        enter_bar_volume=row.enter_bar_volume,
        exit_bar_volume=row.exit_bar_volume,
    )


__all__ = ["EnumCsvScan"]
