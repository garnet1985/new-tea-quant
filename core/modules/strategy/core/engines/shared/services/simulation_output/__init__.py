"""simulation_output — 仿真 version 产物布局服务（命名 / 定位 / 边界 IO）。

消费者: enumerator, price_factor, portfolio
其它: fingerprints（period 在 strategy_settings）

职责: 统一文件名、路径、json/txt 读写方式。
不负责: runtime/CSV/overall/performance 的业务内容模型（各引擎私有）。
"""

from .file_names import (
    ENTITIES_SUBDIR,
    ENTITY_IDS_FILE,
    ENUM_VERSION_REQUIRED_FILES,
    GLOBAL_PREFIX,
    GOAL_ACHIEVEMENTS_SUFFIX,
    OVERALL_REPORT_FILE,
    PERFORMANCE_FILE,
    RUNTIME_ENV_FILE,
    STOCK_INVESTMENTS_SUFFIX,
)
from .io import ArtifactIO
from .enumerator_output import EnumOutput
from .paths import ArtifactPaths, ReportPaths

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
    "ArtifactIO",
    "ArtifactPaths",
    "ReportPaths",
    "EnumOutput",
]
