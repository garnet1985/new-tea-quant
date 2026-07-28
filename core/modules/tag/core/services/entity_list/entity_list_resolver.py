"""解析 Tag 计算所需的 entity id 列表。

消费者: Tag
"""

from __future__ import annotations

import logging
from typing import List, Optional

from core.modules.data_contract import DATA_KEY, ContractIssuer
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.enums import TagTargetType

logger = logging.getLogger(__name__)


class TagEntityListResolver:
    """从 scenario settings / ContractIssuer 推导实体列表。"""

    @classmethod
    def resolve(
        cls,
        scenario: Scenario,
        *,
        stock_limit: Optional[int] = None,
    ) -> List[str]:
        target_type = str(
            scenario.settings.get("tag_target_type") or TagTargetType.ENTITY_BASED.value
        ).strip().lower()
        if target_type == TagTargetType.GENERAL.value:
            return ["__general__"]

        entity_ids = cls._load_stock_ids()
        if stock_limit is not None and len(entity_ids) > int(stock_limit):
            logger.warning(
                "实体列表截断 %d → %d（stock_limit）",
                len(entity_ids),
                int(stock_limit),
            )
            entity_ids = entity_ids[: int(stock_limit)]
        return entity_ids

    @classmethod
    def _load_stock_ids(cls) -> List[str]:
        try:
            contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
            rows = list(contract.get_data() or [])
        except Exception as exc:
            logger.error("加载 stock.list 失败: %s", exc, exc_info=True)
            return []
        return [str(row.get("id")).strip() for row in rows if row.get("id")]


__all__ = ["TagEntityListResolver"]
