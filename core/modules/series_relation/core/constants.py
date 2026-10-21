"""序列关系模块常量（非用户配置）。"""

from __future__ import annotations

# 单次比较最多系列条数；超限拒跑，不进 settings。
MAX_SERIES = 6

SETTINGS_FILE_NAME = "settings.py"

NORMALIZE_MODES = frozenset({"none", "zscore", "minmax", "index_100"})
FILL_MODES = frozenset({"none", "ffill"})

__all__ = [
    "MAX_SERIES",
    "SETTINGS_FILE_NAME",
    "NORMALIZE_MODES",
    "FILL_MODES",
]
