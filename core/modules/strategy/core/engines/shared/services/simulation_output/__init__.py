"""simulation_output — 仿真 version 产物布局与枚举读取。

消费者: enumerator, price_factor, portfolio
其它: fingerprints（period 在 strategy_settings）

职责:
- 布局: file_names / paths / io / EnumOutput
- 读句柄: EnumSource（runtime 投影 + 委托读 investments CSV）
- CSV 行模型: investment_csv（E 写、P/O 读，同一份）

不负责: P/O 自有产物写盘；enumerator RuntimeEnv 业务写模型（仍在 artifacts）
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
from .enum_source import EnumRuntimeMeta, EnumSource
from .investment_csv import (
    EntityInvestmentCsv,
    GoalAchievementCsv,
    GoalAchievementRow,
    InvestmentRow,
)
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
    "EnumRuntimeMeta",
    "EnumSource",
    "EntityInvestmentCsv",
    "GoalAchievementCsv",
    "GoalAchievementRow",
    "InvestmentRow",
]
