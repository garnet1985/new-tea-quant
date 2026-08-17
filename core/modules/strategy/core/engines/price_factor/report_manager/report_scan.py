"""价格回测 build 共用：扫描 entities CSV（仅 build 用）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore, PriceInvestmentRow
from core.modules.strategy.core.engines.price_factor.report_manager.runtime_env import (
    PriceRuntimeEnv,
)


@dataclass
class PriceCsvScan:
    """一次扫盘结果，供 OverallReport / EntityListReport 共用。"""

    total_entities: int
    investments_by_entity: Dict[str, List[PriceInvestmentRow]] = field(default_factory=dict)
    strategy_key: str = ""
    strategy_path: str = ""
    version_id: int = 0
    enum_version_id: str = ""
    backtest_period: Dict[str, str] = field(default_factory=dict)

    @property
    def all_investments(self) -> List[PriceInvestmentRow]:
        rows: List[PriceInvestmentRow] = []
        for part in self.investments_by_entity.values():
            rows.extend(part)
        return rows

    @classmethod
    def collect(
        cls,
        output_dir: Path,
        *,
        entity_ids: Optional[List[str]] = None,
        strategy_key: str = "",
        version_id: int = 0,
    ) -> "PriceCsvScan":
        runtime = PriceRuntimeEnv.load(output_dir)
        ids = list(entity_ids) if entity_ids is not None else list(runtime.entity_ids or [])
        store = ArtifactStore.at(output_dir, kind=SimulateKind.PRICE_FACTOR)
        by_entity = store.load_all_price_investments(ids)
        period = dict(runtime.period or {})
        return cls(
            total_entities=max(0, len(ids)),
            investments_by_entity=by_entity,
            strategy_key=str(strategy_key or runtime.strategy_key or ""),
            strategy_path=str(runtime.strategy_path or runtime.strategy_key or ""),
            version_id=int(version_id or runtime.version_id or 0),
            enum_version_id=str(runtime.enum_version_id or ""),
            backtest_period={
                "start_date": str(period.get("start_date") or "").strip(),
                "end_date": str(period.get("end_date") or "").strip(),
            },
        )


__all__ = ["PriceCsvScan"]
