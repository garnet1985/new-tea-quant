"""Strategy 并行执行（BacktestEngine）。"""

from .enum_job_pipeline import (
    build_enumeration_payload,
    execute_enumeration_job,
    run_enumeration_sliced_via_backtest_engine,
    run_enumeration_timeline_via_backtest_engine,
)
from .price_job_pipeline import (
    build_price_factor_payload,
    execute_price_factor_job,
    run_price_factor_timeline_via_backtest_engine,
)
from .scanner_job_pipeline import (
    build_scanner_payload,
    execute_scanner_job,
    run_scanner_timeline_via_backtest_engine,
    run_scanner_worker_payload,
)
from .stock_job_pipeline import job_report_to_job_result, job_progress_payload
from .worker_runtime import (
    bootstrap_strategy_worker_data_manager,
    create_strategy_worker_data_manager,
    release_strategy_worker_runtime,
)

__all__ = [
    "build_enumeration_payload",
    "build_price_factor_payload",
    "bootstrap_strategy_worker_data_manager",
    "create_strategy_worker_data_manager",
    "execute_enumeration_job",
    "execute_price_factor_job",
    "job_report_to_job_result",
    "job_progress_payload",
    "release_strategy_worker_runtime",
    "run_enumeration_sliced_via_backtest_engine",
    "run_enumeration_timeline_via_backtest_engine",
    "run_price_factor_timeline_via_backtest_engine",
    "run_scanner_timeline_via_backtest_engine",
    "run_scanner_worker_payload",
    "build_scanner_payload",
    "execute_scanner_job",
]
