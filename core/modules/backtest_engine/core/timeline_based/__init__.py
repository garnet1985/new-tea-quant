"""Timeline-based调度文件夹

基于独立时间线调度回测的模式。

特点：
- 每个entity独立时间线
- 逐entity、逐交易日推进
- Tag默认模式
"""
from core.modules.backtest_engine.core.timeline_based.config import TimelineConfig
from core.modules.backtest_engine.core.timeline_based.probe import Probe
from core.modules.backtest_engine.core.timeline_based.planner import TimelinePlanner, DispatchPlan, JobBatch
from core.modules.backtest_engine.core.timeline_based.executor import TimelineExecutor, ExecutionResult
from core.modules.backtest_engine.core.timeline_based.executor_duckdb import TimelineExecutorDuckDB

__all__ = [
    "TimelineConfig",
    "Probe",
    "TimelinePlanner",
    "DispatchPlan",
    "JobBatch",
    "TimelineExecutor",
    "ExecutionResult",
    "TimelineExecutorDuckDB",
]