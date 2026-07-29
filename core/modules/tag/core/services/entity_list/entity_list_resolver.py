"""解析 Tag 计算所需的 entity id 列表。

消费者: Tag

- ``data.base`` scope=global → 哨兵 ``GLOBAL_ENTITY_ID``
- ``data.base`` per_entity → ``meta.list_data_key`` 对应 list（stock.list / index.list）
"""

from __future__ import annotations

import logging
from typing import List, Optional

from core.modules.data_contract import DATA_KEY, ContractIssuer
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.global_based.constants import GLOBAL_ENTITY_ID
from core.modules.tag.core.engines.per_entity.shared.tag_settings.data_settings import (
    DataSettings,
)
from core.modules.tag.core.enums import TagTargetType

logger = logging.getLogger(__name__)


class TagEntityListResolver:
    """从 scenario base / ContractIssuer 推导实体列表。"""

    @classmethod
    def resolve(
        cls,
        scenario: Scenario,
        *,
        stock_limit: Optional[int] = None,
        entity_limit: Optional[int] = None,
    ) -> List[str]:
        # 兼容旧 stub；产品入口以 data.base scope 为准
        target_type = str(
            scenario.settings.get("tag_target_type") or TagTargetType.ENTITY_BASED.value
        ).strip().lower()
        if target_type == TagTargetType.GENERAL.value:
            return [GLOBAL_ENTITY_ID]

        base_key = cls._base_data_key(scenario)
        if base_key and DataSettings.is_global(base_key):
            return [GLOBAL_ENTITY_ID]

        list_key = cls.resolve_list_data_key(scenario)
        entity_ids = cls._load_entity_ids(list_key)

        limit = entity_limit if entity_limit is not None else stock_limit
        if limit is not None and len(entity_ids) > int(limit):
            logger.warning(
                "实体列表截断 %d → %d（entity_limit）list=%s",
                len(entity_ids),
                int(limit),
                list_key,
            )
            entity_ids = entity_ids[: int(limit)]
        return entity_ids

    @classmethod
    def resolve_list_data_key(cls, scenario: Scenario) -> str:
        """从 base / attach_to 读 per_entity 声明的 ``list_data_key``。"""
        base_key = cls._base_data_key(scenario)
        if not base_key:
            logger.warning(
                "scenario %s 缺少 attach_to / data.base，回退 %s",
                scenario.name,
                DATA_KEY.STOCK_LIST,
            )
            return DATA_KEY.STOCK_LIST

        if DataSettings.is_global(base_key):
            raise ValueError(
                f"base={base_key!r} 为 global scope，无 list_data_key；"
                f"实体池应为 {[GLOBAL_ENTITY_ID]}"
            )

        try:
            return ContractIssuer.get_list_data_key(base_key)
        except Exception as exc:
            logger.error(
                "读取 base=%s list_data_key 失败，回退 %s: %s",
                base_key,
                DATA_KEY.STOCK_LIST,
                exc,
                exc_info=True,
            )
            return DATA_KEY.STOCK_LIST

    @classmethod
    def _base_data_key(cls, scenario: Scenario) -> str:
        attach = str(scenario.attach_to_data_key or "").strip()
        if attach:
            return attach
        settings = scenario.settings if isinstance(scenario.settings, dict) else {}
        data = settings.get("data")
        if isinstance(data, dict):
            base = data.get("base")
            if isinstance(base, dict):
                return str(base.get("data_key") or "").strip()
        return ""

    @classmethod
    def _load_entity_ids(cls, list_data_key: str) -> List[str]:
        try:
            contract = ContractIssuer.issue(list_data_key, fill_in_data=True)
            rows = list(contract.get_data() or [])
        except Exception as exc:
            logger.error(
                "加载实体列表失败 list_data_key=%s: %s",
                list_data_key,
                exc,
                exc_info=True,
            )
            return []
        return [str(row.get("id")).strip() for row in rows if row.get("id")]


__all__ = ["TagEntityListResolver"]
