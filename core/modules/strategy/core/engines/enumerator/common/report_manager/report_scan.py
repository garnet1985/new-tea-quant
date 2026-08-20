"""枚举报告 build 共用：扫描 entities CSV（仅 build 用，presenter 不读）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.modules.strategy.core.engines.enumerator.common.artifacts.runtime_env import (
    RuntimeEnv,
)
from core.modules.strategy.core.services.artifacts import EnumerateStore, InvestmentRow


@dataclass
class EnumCsvScan:
    """一次扫盘结果，供 OverallReport / EntityListReport 共用。"""

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

        store = EnumerateStore.at(output_dir)
        investments_by_entity: Dict[str, List[InvestmentRow]] = {}
        for entity_id, rows in store.load_all_investments().items():
            investments_by_entity[entity_id] = list(rows)

        return cls(
            total_entities=max(0, total),
            investments_by_entity=investments_by_entity,
            strategy_key=str(strategy_key or runtime.strategy_key or ""),
            strategy_path=str(runtime.strategy_path or runtime.strategy_key or ""),
            version_id=int(version_id or runtime.version_id or 0),
            execution_mode=str(runtime.execution_mode or ""),
            backtest_period=period_dict,
        )


__all__ = ["EnumCsvScan"]
