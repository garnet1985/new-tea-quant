"""策略仿真产物读 IO（overall / entity_list / 单股 artifacts）。

BFF report hydrate / step_report / stock_detail 经 Facade 调用，勿 deep-import ArtifactStore。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StrategyReportIo:
    """磁盘报告读模型。"""

    @classmethod
    def load_overall_report_ui(
        cls, step: str, output_dir: Path
    ) -> Optional[Dict[str, Any]]:
        """读 ``overall_report.json`` → ``to_ui_dict()``；缺失或失败返回 ``None``。"""
        from core.modules.strategy.core.services.artifacts import ArtifactStore

        try:
            kind = ArtifactStore.parse_kind(step)
        except ValueError:
            return None
        store = ArtifactStore.for_kind(kind).at(output_dir)
        if not store.file("overall_report").is_file():
            return None
        try:
            if step == "enum":
                from core.modules.strategy.core.engines.enumerator.common.report_manager.overall_report import (
                    OverallReport,
                )
            elif step == "price":
                from core.modules.strategy.core.engines.price_factor.report_manager.overall_report import (
                    OverallReport,
                )
            else:
                from core.modules.strategy.core.engines.portfolio.report_manager.overall_report import (
                    OverallReport,
                )
            return OverallReport.load(output_dir).to_ui_dict()
        except Exception:
            logger.exception("load overall_report ui failed step=%s dir=%s", step, output_dir)
            return None

    @classmethod
    def load_entity_list_ui(
        cls, step: str, output_dir: Path
    ) -> Optional[Dict[str, Any]]:
        """读 ``entity_list`` → ``to_ui_dict()``（未按实体过滤）。"""
        from core.modules.strategy.core.services.artifacts import ArtifactStore

        try:
            kind = ArtifactStore.parse_kind(step)
        except ValueError:
            return None
        store = ArtifactStore.for_kind(kind).at(output_dir)
        if not store.file("entity_list").is_file():
            return None
        try:
            if step == "enum":
                from core.modules.strategy.core.engines.enumerator.common.report_manager.entity_list_report import (
                    EntityListReport,
                )
            elif step == "price":
                from core.modules.strategy.core.engines.price_factor.report_manager.entity_list_report import (
                    EntityListReport,
                )
            else:
                return None
            return EntityListReport.load(output_dir).to_ui_dict()
        except Exception:
            logger.exception("load entity_list ui failed step=%s dir=%s", step, output_dir)
            return None

    @classmethod
    def step_dir_has_entity(
        cls, step: str, output_dir: Path, entity_id: str
    ) -> bool:
        """目录是否含该实体产物（``ArtifactStore.has_investments``）。"""
        from core.modules.strategy.core.services.artifacts import ArtifactStore

        eid = str(entity_id or "").strip()
        if not eid or not Path(output_dir).is_dir():
            return False
        try:
            store = ArtifactStore.for_kind(step).at(output_dir)
            return bool(store.has_investments(eid))
        except Exception:
            return False

    @classmethod
    def enum_entity_has_data(cls, output_dir: Path, entity_id: str) -> bool:
        eid = str(entity_id or "").strip()
        if not eid:
            return False
        from core.modules.strategy.core.engines.shared.enum_result_contract import (
            EnumResultsManager,
        )

        return bool(EnumResultsManager.at(output_dir).results(eid))

    @classmethod
    def price_entity_has_investments(cls, output_dir: Path, entity_id: str) -> bool:
        eid = str(entity_id or "").strip().replace("/", "_")
        if not eid:
            return False
        from core.modules.strategy.core.services.artifacts import PriceFactorStore

        return PriceFactorStore.at(output_dir).has_investments(eid)

    @classmethod
    def load_price_investments(cls, output_dir: Path, entity_id: str) -> List[Any]:
        from core.modules.strategy.core.services.artifacts import PriceFactorStore

        return list(PriceFactorStore.at(output_dir).investments(entity_id) or [])

    @classmethod
    def load_price_goals(cls, output_dir: Path, entity_id: str) -> List[Any]:
        from core.modules.strategy.core.services.artifacts import PriceFactorStore

        return list(PriceFactorStore.at(output_dir).goals(entity_id) or [])

    @classmethod
    def load_enum_entity_results(cls, output_dir: Path, entity_id: str) -> List[Any]:
        from core.modules.strategy.core.engines.shared.enum_result_contract import (
            EnumResultsManager,
        )

        try:
            return list(EnumResultsManager.at(output_dir).results(entity_id))
        except Exception:
            logger.exception(
                "load enum entity results failed dir=%s entity=%s",
                output_dir,
                entity_id,
            )
            return []


__all__ = ["StrategyReportIo"]
