"""一层回测结束后的诊断：收集 → 结论 → 建议 → 落盘。

边界:
- 负责: 该层产物上的事实 / 结论 / 建议
- 不负责: 战役格子、sz 切片 SHAP、回测引擎
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.analyzer.steps.layer.advise import EnumerateAdvise
from core.modules.strategy.core.engines.analyzer.steps.layer.conclude import EnumerateConclude
from core.modules.strategy.core.engines.analyzer.steps.layer.gather import EnumerateGather
from core.modules.strategy.core.engines.analyzer.steps.layer.persist import (
    LayerPersist,
    load_layer_report,
)
from core.modules.strategy.core.engines.analyzer.steps.layer.present import LayerPresenter
from core.modules.strategy.core.engines.analyzer.steps.layer.portfolio_advise import (
    PortfolioAdvise,
)
from core.modules.strategy.core.engines.analyzer.steps.layer.portfolio_conclude import (
    PortfolioConclude,
)
from core.modules.strategy.core.engines.analyzer.steps.layer.portfolio_gather import (
    PortfolioGather,
)
from core.modules.strategy.core.engines.analyzer.steps.layer.price_advise import PriceAdvise
from core.modules.strategy.core.engines.analyzer.steps.layer.price_conclude import (
    PriceConclude,
)
from core.modules.strategy.core.engines.analyzer.steps.layer.price_gather import PriceGather
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore

_Gather = Callable[[ArtifactStore], Dict[str, Any]]
_Conclude = Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]]
_Advise = Callable[
    [Sequence[Mapping[str, Any]], Mapping[str, Any]], Sequence[Mapping[str, Any]]
]
_Handlers = Tuple[_Gather, _Conclude, _Advise]


class LayerPipeline:
    """哪一层跑完就归因哪一层。"""

    @classmethod
    def run(
        cls,
        store: ArtifactStore,
        *,
        present: bool = True,
        force: bool = False,
    ) -> Dict[str, Any]:
        handlers = _handlers(store.kind)
        if handlers is None:
            return {
                "success": True,
                "skipped": True,
                "reason": "layer_not_implemented",
                "layer": store.kind.value,
                "output_dir": str(store.output_dir.resolve()),
            }
        if not force:
            existing = load_layer_report(store)
            if existing is not None:
                if present:
                    LayerPresenter(
                        existing, report_path=store.file("layer_attribution")
                    ).present()
                existing.setdefault("success", True)
                existing["skipped"] = True
                existing["reason"] = "exists"
                return existing
        gather, conclude, advise = handlers
        facts = gather(store)
        conclusions = list(conclude(facts))
        suggestions = list(advise(conclusions, facts))
        payload = LayerPersist.run(
            store,
            facts=facts,
            conclusions=conclusions,
            suggestions=suggestions,
        )
        if present:
            LayerPresenter(
                payload, report_path=store.file("layer_attribution")
            ).present()
        return payload


def _handlers(kind: SimulateKind) -> Optional[_Handlers]:
    if kind == SimulateKind.ENUMERATE:
        return EnumerateGather.run, EnumerateConclude.run, EnumerateAdvise.run
    if kind == SimulateKind.PRICE_FACTOR:
        return PriceGather.run, PriceConclude.run, PriceAdvise.run
    if kind == SimulateKind.PORTFOLIO:
        return PortfolioGather.run, PortfolioConclude.run, PortfolioAdvise.run
    return None
