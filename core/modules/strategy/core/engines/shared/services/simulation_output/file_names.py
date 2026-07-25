"""仿真 version 目录硬编码文件名（布局服务）。

消费者: enumerator, price_factor, portfolio, scanner（若约定同构）
边界: 只放文件名 / 子目录 / 必有文件元组；内容模型各引擎私有
"""
from __future__ import annotations

# 全局产物（0_ 前缀 — 目录列表中排在 per-entity 文件之前）
GLOBAL_PREFIX = "0_"
RUNTIME_ENV_FILE = f"{GLOBAL_PREFIX}runtime_env.json"
ENTITY_IDS_FILE = f"{GLOBAL_PREFIX}entity_ids.txt"
PERFORMANCE_FILE = f"{GLOBAL_PREFIX}performance.json"
OVERALL_REPORT_FILE = f"{GLOBAL_PREFIX}overall_report.json"

# 每股 CSV 子目录
ENTITIES_SUBDIR = "entities"

# 枚举实体 CSV 后缀（布局约定；行 schema 由各引擎私有解析）
STOCK_INVESTMENTS_SUFFIX = "_stock_investments.csv"
GOAL_ACHIEVEMENTS_SUFFIX = "_goal_achievements.csv"

ENUM_VERSION_REQUIRED_FILES = (
    RUNTIME_ENV_FILE,
    ENTITY_IDS_FILE,
    PERFORMANCE_FILE,
    OVERALL_REPORT_FILE,
)

__all__ = [
    "ENTITIES_SUBDIR",
    "ENTITY_IDS_FILE",
    "ENUM_VERSION_REQUIRED_FILES",
    "GLOBAL_PREFIX",
    "GOAL_ACHIEVEMENTS_SUFFIX",
    "OVERALL_REPORT_FILE",
    "PERFORMANCE_FILE",
    "RUNTIME_ENV_FILE",
    "STOCK_INVESTMENTS_SUFFIX",
]
