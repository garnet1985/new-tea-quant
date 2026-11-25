"""序列关系模块常量（非用户配置）。"""

from __future__ import annotations

# 单次比较最多系列条数；超限拒跑，不进 settings。
MAX_SERIES = 6

SETTINGS_FILE_NAME = "settings.py"

NORMALIZE_MODES = frozenset({"none", "zscore", "minmax", "index_100"})
FILL_MODES = frozenset({"none", "ffill"})

# series 源：契约 data_key（默认）或回测产物
SOURCE_DATA_KEY = "data_key"
SOURCE_STRATEGY_SIM = "strategy_sim"
SERIES_SOURCES = frozenset({SOURCE_DATA_KEY, SOURCE_STRATEGY_SIM})

STRATEGY_SIM_LAYERS = frozenset({"portfolio", "price"})
STRATEGY_SIM_METRICS = frozenset({"equity", "cum_exit_roi"})
# (layer, metric) 白名单
STRATEGY_SIM_LAYER_METRICS = frozenset(
    {
        ("portfolio", "equity"),
        ("price", "cum_exit_roi"),
    }
)

TRANSFORM_MODES = frozenset({"none", "returns"})

__all__ = [
    "MAX_SERIES",
    "SETTINGS_FILE_NAME",
    "NORMALIZE_MODES",
    "FILL_MODES",
    "SOURCE_DATA_KEY",
    "SOURCE_STRATEGY_SIM",
    "SERIES_SOURCES",
    "STRATEGY_SIM_LAYERS",
    "STRATEGY_SIM_METRICS",
    "STRATEGY_SIM_LAYER_METRICS",
    "TRANSFORM_MODES",
]
