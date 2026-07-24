"""simulation_input — 枚举 version 产物契约整块（路径 + runtime + CSV + 加载）。

消费者: enumerator, price_factor, portfolio
其它: fingerprints, entity_loader, tests

整块 keep：artifact_paths / runtime_snapshot / stock_investments / enum_loader 不拆。
enumerator ReportManager 的 RuntimeReport / InvestmentsReport 写门面仍留在 enumerator。
"""

from .artifact_paths import (
    ENTITIES_SUBDIR,
    ENTITY_IDS_FILE,
    ENUM_VERSION_REQUIRED_FILES,
    GLOBAL_PREFIX,
    NON_GOAL_EXIT_REASONS,
    OVERALL_REPORT_FILE,
    PERFORMANCE_DETAIL_FULL,
    PERFORMANCE_DETAIL_SUMMARY,
    PERFORMANCE_FILE,
    RUNTIME_ENV_FILE,
    ReportPaths,
)
from .enum_loader import EnumVersionData, load_enum_version, resolve_enum_version_dir
from .runtime_snapshot import (
    BacktestPeriod,
    RuntimeSnapshot,
    SavedRuntimeArtifacts,
    SettingsSnapshot,
    SystemEnv,
)
from .stock_investments import (
    GoalAchievementRow,
    GoalAchievements,
    InvestmentRow,
    StockInvestments,
)

__all__ = [
    "ENTITIES_SUBDIR",
    "ENTITY_IDS_FILE",
    "ENUM_VERSION_REQUIRED_FILES",
    "GLOBAL_PREFIX",
    "NON_GOAL_EXIT_REASONS",
    "OVERALL_REPORT_FILE",
    "PERFORMANCE_DETAIL_FULL",
    "PERFORMANCE_DETAIL_SUMMARY",
    "PERFORMANCE_FILE",
    "RUNTIME_ENV_FILE",
    "ReportPaths",
    "EnumVersionData",
    "load_enum_version",
    "resolve_enum_version_dir",
    "BacktestPeriod",
    "RuntimeSnapshot",
    "SavedRuntimeArtifacts",
    "SettingsSnapshot",
    "SystemEnv",
    "GoalAchievementRow",
    "GoalAchievements",
    "InvestmentRow",
    "StockInvestments",
]
