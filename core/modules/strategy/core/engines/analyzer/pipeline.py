"""战役编排：读 attribution.py → 展开格子 → simulate → 拼表 → 归因 → 总结 → 落盘。

边界:
- 负责: 步骤顺序
- 不负责: overlay、settings 解析、单 version 的 Prepare→Analyze→Report
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

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
    PARAMETER_TASK_ID,
    ROLLING_TASK_ID,
    PersistStep,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.report import CampaignReportStep
from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize import SummarizeStep
from core.modules.strategy.core.engines.analyzer.steps.rolling.config import RollingSettings
from core.modules.strategy.core.engines.analyzer.steps.rolling.summarize import RollingSummarizeStep
from core.modules.strategy.core.engines.analyzer.steps.rolling.windows import WindowExpander
from core.modules.strategy.core.services.discovery import DiscoveryService


class AttributionPipeline:
    """战役流程入口。"""

    @classmethod
    def run(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        folder = cls._resolve_folder(key_or_id)
        config = AttributionSettings.load(folder)
        if not config.has_parameter:
            raise ValueError(
                "attribution.py 没有 matrix / versions；参数战役请写这两项之一，滚动窗口用 CLI sw"
            )
        cells = CellExpander.expand_from_folder(folder, config)
        tasks = AttributionTask.from_cells(cells, config)
        executed = ExecuteStep.run(folder, tasks, ignore_cache=ignore_cache)
        gathered = GatherStep.run(folder, tasks, executed)
        attributed = AttributeStep.run(gathered)
        summarized = SummarizeStep.run(attributed)
        assembled = CampaignReportStep.run(
            folder,
            config,
            cells,
            tasks,
            executed=executed,
            gathered=gathered,
            attributed=attributed,
            summarized=summarized,
        )
        return PersistStep.run(
            folder,
            config,
            assembled,
            executed=executed,
            task_id=PARAMETER_TASK_ID,
            task_kind="parameter",
        )

    @staticmethod
    def _resolve_folder(key_or_id: Union[str, Path]) -> Path:
        path = Path(key_or_id)
        if path.is_dir() and (path / ATTRIBUTION_FILE_NAME).is_file():
            return path
        return DiscoveryService.resolve_strategy_folder(str(key_or_id))


class RollingPipeline:
    """滚动验证：同一套旋钮，对照声明窗口。"""

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
        tasks = AttributionTask.from_cells(cells, config)
        executed = ExecuteStep.run(folder, tasks, ignore_cache=ignore_cache)
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
