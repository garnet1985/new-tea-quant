"""战役编排：读 attribution.py → 展开格子 → 按层 simulate → 拼表 → 归因 → 总结 → 落盘。

边界:
- 负责: 步骤顺序；层由调用方选定（sea / spa / soa）
- 不负责: overlay、settings 解析、单 version 切片
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.modules.strategy.core.engines.analyzer.steps.campaign.attribute import AttributeStep
from core.modules.strategy.core.engines.analyzer.steps.campaign.cells import (
    AttributionTask,
    CellExpander,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.config import (
    ATTRIBUTION_FILE_NAME,
    AttributionSettings,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.execute import ExecuteStep
from core.modules.strategy.core.engines.analyzer.steps.campaign.gather import GatherStep
from core.modules.strategy.core.engines.analyzer.steps.campaign.persist import (
    ROLLING_TASK_ID,
    PersistStep,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.report import CampaignReportStep
from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize import SummarizeStep
from core.modules.strategy.core.engines.analyzer.steps.campaign.trades import TradesStep
from core.modules.strategy.core.engines.analyzer.steps.rolling.config import RollingSettings
from core.modules.strategy.core.engines.analyzer.steps.rolling.summarize import RollingSummarizeStep
from core.modules.strategy.core.engines.analyzer.steps.rolling.windows import WindowExpander
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.discovery import DiscoveryService

_LAYER_TASK = {
    SimulateKind.ENUMERATE: "enumerate",
    SimulateKind.PRICE_FACTOR: "price_factor",
    SimulateKind.PORTFOLIO: "portfolio",
}


class AttributionPipeline:
    """按层战役入口（sea / spa / soa）。"""

    @classmethod
    def run(
        cls,
        key_or_id: Union[str, Path],
        *,
        kind: Union[SimulateKind, str],
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        layer = (
            kind
            if isinstance(kind, SimulateKind)
            else SimulateKind(str(kind).strip().lower())
        )
        if layer not in _LAYER_TASK:
            raise ValueError(f"不支持的归因层: {kind!r}")
        folder = cls._resolve_folder(key_or_id)
        config = AttributionSettings.load(folder)
        if not config.has_parameter:
            raise ValueError(
                "attribution.py 没有 overlays / matrix / versions；"
                "请先配置对照格，再跑 sea / spa / soa"
            )
        plan = CellExpander.plan_from_folder(folder, config)
        unique_tasks = ExecuteStep.unique_tasks(
            AttributionTask.from_cells(plan.execute_source_cells(), kind=layer)
        )
        executed = ExecuteStep.run(
            folder, unique_tasks, kind=layer, ignore_cache=ignore_cache
        )
        unique_cells = [task.cell for task in unique_tasks]
        trades: Optional[Dict[str, Any]] = None
        if layer == SimulateKind.PRICE_FACTOR:
            trades = TradesStep.run(folder, unique_cells, executed)
        families = {}
        for name, cells in plan.families():
            family_executed = ExecuteStep.bind(executed, unique_cells, cells)
            tasks = AttributionTask.from_cells(cells, kind=layer)
            gathered = GatherStep.run(folder, tasks, family_executed)
            attributed = AttributeStep.run(gathered, layer=layer.value)
            summarized = SummarizeStep.run(attributed, layer=layer.value)
            families[name] = CampaignReportStep.run(
                folder,
                config,
                cells,
                tasks,
                executed=family_executed,
                gathered=gathered,
                attributed=attributed,
                summarized=summarized,
                family=name,
            )
        assembled = CampaignReportStep.merge(
            config, executed, families, trades=trades or {}
        )
        assembled["layer"] = layer.value
        assembled["strategy_key"] = Path(folder).name
        task_id = _LAYER_TASK[layer]
        return PersistStep.run(
            folder,
            config,
            assembled,
            executed=executed,
            task_id=task_id,
            task_kind=task_id,
        )

    @staticmethod
    def _resolve_folder(key_or_id: Union[str, Path]) -> Path:
        path = Path(key_or_id)
        if path.is_dir() and (path / ATTRIBUTION_FILE_NAME).is_file():
            return path
        return DiscoveryService.resolve_strategy_folder(str(key_or_id))


class RollingPipeline:
    """滚动验证：同一套旋钮，对照声明窗口。默认每窗跑到 portfolio。"""

    @classmethod
    def run(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        folder = cls._resolve_folder(key_or_id)
        config = RollingSettings.load(folder)
        cells = WindowExpander.expand_from_folder(folder, config)
        layer = SimulateKind.PORTFOLIO
        tasks = AttributionTask.from_cells(cells, kind=layer)
        executed = ExecuteStep.run(
            folder, tasks, kind=layer, ignore_cache=ignore_cache
        )
        gathered = GatherStep.run(folder, tasks, executed)
        summarized = RollingSummarizeStep.run(gathered)
        assembled = CampaignReportStep.run(
            folder,
            config,
            cells,
            tasks,
            executed=executed,
            gathered=gathered,
            attributed={
                "status": summarized.get("status"),
                "n": summarized.get("n", 0),
                "layers": {},
                "contributions": {},
            },
            summarized=summarized,
        )
        assembled["mode"] = "rolling"
        assembled["headline"] = summarized.get("headline")
        return PersistStep.run(
            folder,
            config,
            assembled,
            executed=executed,
            task_id=ROLLING_TASK_ID,
            task_kind="rolling",
        )

    @staticmethod
    def _resolve_folder(key_or_id: Union[str, Path]) -> Path:
        path = Path(key_or_id)
        if path.is_dir() and (path / ATTRIBUTION_FILE_NAME).is_file():
            return path
        return DiscoveryService.resolve_strategy_folder(str(key_or_id))
