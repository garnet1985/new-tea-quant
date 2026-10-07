"""战役报告步：组装返回体 + 终端展示。

pipeline 只调 ``CampaignReportStep.run/merge(..., layer=)``；层差异在子类。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Type

from core.modules.strategy.core.enums import SimulateKind

from ..layers import declare_layer, pick_layer
from ..plan import AttributionCell, AttributionTask
from .base import ReportBase
from .present import CampaignPresenter

EnumerateReport = declare_layer(
    "EnumerateReport", ReportBase, "enumerate", SimulateKind.ENUMERATE
)
PriceReport = declare_layer(
    "PriceReport", ReportBase, "price_factor", SimulateKind.PRICE_FACTOR
)
PortfolioReport = declare_layer(
    "PortfolioReport", ReportBase, "portfolio", SimulateKind.PORTFOLIO
)

_BY_LAYER: dict[str, Type[ReportBase]] = {
    "enumerate": EnumerateReport,
    "price_factor": PriceReport,
    "portfolio": PortfolioReport,
}


class CampaignReportStep:
    """报告步门面：按层分发到对应报告类。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[ReportBase]:
        return pick_layer(_BY_LAYER, layer, PortfolioReport)

    @classmethod
    def run(
        cls,
        folder: Path,
        config: Any,
        cells: Sequence[AttributionCell],
        tasks: Sequence[AttributionTask],
        *,
        executed: Dict[str, Any],
        gathered: Dict[str, Any],
        attributed: Dict[str, Any],
        summarized: Dict[str, Any],
        family: str = "",
        layer: str = "",
    ) -> Dict[str, Any]:
        focus = layer
        if not focus and tasks:
            focus = str(getattr(tasks[0].kind, "value", tasks[0].kind) or "")
        if not focus:
            focus = str(getattr(config, "layer", "") or "")
        return cls.for_layer(focus).run(
            folder,
            config,
            cells,
            tasks,
            executed=executed,
            gathered=gathered,
            attributed=attributed,
            summarized=summarized,
            family=family,
        )

    @classmethod
    def merge(
        cls,
        config: Any,
        executed: Mapping[str, Any],
        families: Mapping[str, Mapping[str, Any]],
        *,
        trades: Optional[Mapping[str, Any]] = None,
        layer: str = "",
    ) -> Dict[str, Any]:
        focus = layer or str(getattr(config, "layer", "") or "")
        return cls.for_layer(focus).merge(
            config, executed, families, trades=trades
        )


__all__ = [
    "CampaignPresenter",
    "CampaignReportStep",
    "EnumerateReport",
    "PortfolioReport",
    "PriceReport",
    "ReportBase",
]
