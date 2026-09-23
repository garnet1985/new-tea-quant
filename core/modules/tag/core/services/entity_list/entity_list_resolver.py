"""解析 Tag 计算所需的 entity id 列表。

消费者: Tag

- ``data.base`` scope=global（含非时序 list / 时序 macro）→ 哨兵 ``GLOBAL_ENTITY_ID``
- ``data.base`` per_entity → ``meta.list_data_key`` 对应 list（stock.list / index.list）
- per_entity：可选 ``TagHooks.to_entity_list`` → 与入参取交 → 排序 → ``entity_limit``
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Sequence, TYPE_CHECKING

from core.modules.data_contract import ContractIssuer
from core.modules.data_contract.contracts import DATA_KEY
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.global_based.constants import GLOBAL_ENTITY_ID
from core.modules.tag.core.engines.shared.hooks.hook_params import TagContext
from core.modules.tag.core.engines.shared.hooks.runtime import TagHookRuntime
from core.modules.tag.core.engines.shared.tag_settings.data_settings import (
    DataSettings,
)

if TYPE_CHECKING:
    from core.modules.tag.core.engines.shared.tag_settings.tag_settings import (
        TagSettings,
    )
    from core.modules.tag.core.services.discovery.data.discovered_tag import (
        DiscoveredTagInfo,
    )

logger = logging.getLogger(__name__)


class TagEntityListResolver:
    """从 scenario base / ContractIssuer 推导实体列表。"""

    @classmethod
    def resolve(
        cls,
        scenario: Scenario,
        *,
        entity_limit: Optional[int] = None,
        tag_info: Optional["DiscoveredTagInfo"] = None,
        settings: Optional["TagSettings"] = None,
        apply_hook: bool = False,
    ) -> List[str]:
        base_key = cls._base_data_key(scenario)
        if base_key and DataSettings.is_global(base_key):
            return [GLOBAL_ENTITY_ID]

        list_key = cls.resolve_list_data_key(scenario)
        entity_ids = cls._normalize_ids(cls._load_entity_ids(list_key))

        if apply_hook and tag_info is not None and settings is not None:
            entity_ids = cls._apply_hook(tag_info, settings, entity_ids)

        entity_ids = sorted(entity_ids)

        if entity_limit is not None and len(entity_ids) > int(entity_limit):
            logger.warning(
                "实体列表截断 %d → %d（entity_limit）list=%s",
                len(entity_ids),
                int(entity_limit),
                list_key,
            )
            entity_ids = entity_ids[: int(entity_limit)]
        return entity_ids

    @classmethod
    def _apply_hook(
        cls,
        tag_info: "DiscoveredTagInfo",
        settings: "TagSettings",
        entity_list: List[str],
    ) -> List[str]:
        runtime, err = TagHookRuntime.from_tag_info(tag_info, settings)
        if runtime is None:
            logger.error(
                "to_entity_list: hooks 加载失败，使用全表结果 tag=%s err=%s",
                getattr(tag_info, "key", "") or getattr(tag_info, "unique_relative_path", ""),
                (err or {}).get("error"),
            )
            return entity_list

        tag_key = str(
            getattr(tag_info, "key", None)
            or getattr(tag_info, "unique_relative_path", "")
            or ""
        ).strip()
        tag_path = str(
            getattr(tag_info, "unique_relative_path", "") or tag_key
        ).strip()
        ctx = TagContext.assemble(
            tag_key=tag_key,
            settings=settings,
            entity_list=entity_list,
            tag_path=tag_path,
        )
        allowed = set(entity_list)
        try:
            raw = runtime.call(
                "to_entity_list", ctx, entity_list=list(entity_list)
            )
        except Exception:
            logger.error(
                "to_entity_list 失败 tag=%s，回退全表结果",
                tag_key,
                exc_info=True,
            )
            return entity_list

        out: List[str] = []
        seen = set()
        for item in raw or []:
            eid = str(item).strip()
            if not eid or eid not in allowed or eid in seen:
                continue
            seen.add(eid)
            out.append(eid)
        return out

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

    @staticmethod
    def _normalize_ids(ids: Optional[Sequence[Any]]) -> List[str]:
        out: List[str] = []
        seen = set()
        for item in ids or []:
            eid = str(item).strip()
            if not eid or eid in seen:
                continue
            seen.add(eid)
            out.append(eid)
        return out


__all__ = ["TagEntityListResolver"]
