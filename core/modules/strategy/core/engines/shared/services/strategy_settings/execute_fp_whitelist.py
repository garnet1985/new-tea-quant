"""``execute_fp`` 白名单：哪些 settings 块进入执行身份。

``execute_fp`` 哈希白名单块 + scope（标的）。
区间和 ``execution_mode`` 在 ``simulation`` 里，不另开第三种指纹。
增删字段只改本文件。
"""

from typing import FrozenSet

# 进入 execute_fp.settings 的功能块
EXECUTE_SETTINGS_FIELDS: FrozenSet[str] = frozenset(
    {
        "core",
        "data",
        "goal",
        "sampling",
        "fees",
        "simulation",
        "portfolio",
        "market_profile",
    }
)

# 明确不进 execute_fp（抽取时直接忽略）
NON_EXECUTE_SETTINGS_FIELDS: FrozenSet[str] = frozenset(
    {
        "meta",
        "is_enabled",
        "scanner",
        "enumerator",
        "analysis",
        "price_simulator",
    }
)

# 白名单 section 内的 UI / 草稿 key，抽取时剥掉
EXECUTE_NESTED_DROP_KEYS: FrozenSet[str] = frozenset(
    {
        "force_exit_when_draft",
    }
)
