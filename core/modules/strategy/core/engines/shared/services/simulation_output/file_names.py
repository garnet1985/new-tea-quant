"""仿真 version 目录硬编码文件名（布局服务）。

消费者: enumerator, price_factor, portfolio
边界: 只放文件名 / 子目录 / 必有文件元组；内容模型各引擎私有
"""
from __future__ import annotations

RUNTIME_ENV_FILE = "runtime_env.json"
ENTITY_IDS_FILE = "entity_ids.txt"
PERFORMANCE_FILE = "performance.json"
OVERALL_REPORT_FILE = "overall_report.json"

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
    "GOAL_ACHIEVEMENTS_SUFFIX",
    "OVERALL_REPORT_FILE",
    "PERFORMANCE_FILE",
    "RUNTIME_ENV_FILE",
    "STOCK_INVESTMENTS_SUFFIX",
]
