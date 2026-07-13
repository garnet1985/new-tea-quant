"""枚举 run 产物：ReportManager + 各阶段 dataclass。"""
from core.modules.strategy.core.engines.enumerator.shared.report_manager.overall_report import (
    EntitySummaryRow,
    OverallReport,
    OverallSummary,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.profiler import (
    DispatchPlanSnapshot,
    JobPerformance,
    MonitorStatsSnapshot,
    ProfilerPerformance,
    SavedPerformanceArtifact,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_manager import (
    ReportManager,
    SavedRunArtifacts,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.runtime_snapshot import (
    BacktestPeriod,
    RuntimeSnapshot,
    SavedRuntimeArtifacts,
    SettingsSnapshot,
    SystemEnv,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
    GoalAchievementRow,
    GoalAchievements,
    InvestmentRow,
    StockInvestments,
)

__all__ = [
    "BacktestPeriod",
    "DispatchPlanSnapshot",
    "EntitySummaryRow",
    "GoalAchievementRow",
    "GoalAchievements",
    "InvestmentRow",
    "JobPerformance",
    "MonitorStatsSnapshot",
    "OverallReport",
    "OverallSummary",
    "ProfilerPerformance",
    "SavedPerformanceArtifact",
    "ReportManager",
    "RuntimeSnapshot",
    "SavedRunArtifacts",
    "SavedRuntimeArtifacts",
    "SettingsSnapshot",
    "StockInvestments",
    "SystemEnv",
]
