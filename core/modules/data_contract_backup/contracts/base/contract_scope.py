from __future__ import annotations

from enum import Enum


class ContractScope(str, Enum):
    """
    规则类 **分片语义**（与 `CONCEPTS.md` 中 scope 一致）：谁需要 `entity_id`、缓存键怎么分域。

    MVP 仅两种：**全局** vs **按实体**；不再保留未使用的 `per_category` 等枚举值。
    """

    GLOBAL = "global"
    PER_ENTITY = "per_entity"
