"""决策者终局报告：本局 trades 走 portfolio 同一套 finalize。

本文件:
- finalize_decision_report: 写入 ``decision/{dm_id}/``，不 allocate 新 portfolio version
  边界: 盯市 / SHIBOR / overall 形状与资金层相同；未走完不要调用
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from core.modules.strategy.core.engines.portfolio.report_manager import ReportManager
from core.modules.strategy.core.engines.portfolio.report_manager.runtime_env import (
    PortfolioRuntimeEnv,
)
from core.modules.strategy.core.engines.portfolio.simulator import PortfolioSimResult
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)


def write_runtime_env(
    session_dir: Union[str, Path],
    *,
    strategy_key: str,
    strategy_path: str,
    version_id: str,
    enum_output_dir: str,
    execute_fp: str = "",
    env_fp: str = "",
    start_date: str = "",
    end_date: str = "",
    market_profile: str = "",
) -> Path:
    vid = str(version_id or "").strip()
    try:
        as_int = int(vid)
    except (TypeError, ValueError):
        as_int = 0
    env = PortfolioRuntimeEnv(
        strategy_key=str(strategy_key or "").strip(),
        strategy_path=str(strategy_path or strategy_key or "").strip(),
        version_id=as_int,
        enum_version_id=vid,
        enum_output_dir=str(enum_output_dir or ""),
        execute_fp=str(execute_fp or ""),
        env_fp=str(env_fp or ""),
        period={"start_date": str(start_date or ""), "end_date": str(end_date or "")},
        market_profile=str(market_profile or "").strip(),
    )
    return env.save(Path(session_dir))


def finalize_decision_report(
    session_dir: Union[str, Path],
    sim: PortfolioSimResult,
    *,
    settings: StrategySettings,
    start_date: str = "",
    end_date: str = "",
    strategy_key: str = "",
    market_profile: str = "",
    load_open_dates: Optional[Callable[..., Any]] = None,
    load_hfq_closes: Optional[Callable[..., Any]] = None,
    load_shibor_overnight: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """把本局模拟结果写成与 portfolio 同结构的报告。"""
    output = Path(session_dir)
    output.mkdir(parents=True, exist_ok=True)
    try:
        vid = int(Path(output).name)
    except (TypeError, ValueError):
        vid = 0
    report = ReportManager(
        output_dir=output,
        strategy_key=str(strategy_key or "").strip(),
        strategy_path=str(strategy_key or "").strip(),
        version_id=vid,
        market_profile=str(market_profile or "").strip() or "china_a_stock",
    )
    extra: Dict[str, Any] = {}
    if load_open_dates is not None:
        extra["load_open_dates"] = load_open_dates
    if load_hfq_closes is not None:
        extra["load_hfq_closes"] = load_hfq_closes
    if load_shibor_overnight is not None:
        extra["load_shibor_overnight"] = load_shibor_overnight
    portfolio = settings.portfolio
    return report.finalize(
        sim,
        period={"start_date": str(start_date or ""), "end_date": str(end_date or "")},
        save_trades=bool(portfolio.output.save_trades),
        save_equity_curve=bool(portfolio.output.save_equity_curve),
        **extra,
    )


__all__ = ["finalize_decision_report", "write_runtime_env"]
