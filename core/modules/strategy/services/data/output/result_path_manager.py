#!/usr/bin/env python3
"""Output path manager for strategy simulation artifacts."""

from dataclasses import dataclass
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ResultPathManager:
    sim_version_dir: Path

    SESSION_SUMMARY_FILE: str = "0_session_summary.json"
    TRADES_FILE: str = "trades.json"
    EQUITY_TIMESERIES_FILE: str = "portfolio_timeseries.json"
    STRATEGY_SUMMARY_FILE: str = "summary_strategy.json"
    METADATA_FILE: str = "0_metadata.json"

    def ensure_root(self) -> Path:
        try:
            self.sim_version_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning(
                "[ResultPathManager] failed to create result dir: dir=%s, error=%s",
                self.sim_version_dir,
                exc,
            )
            raise
        return self.sim_version_dir

    def session_summary_path(self) -> Path:
        return self.ensure_root() / self.SESSION_SUMMARY_FILE

    def trades_path(self) -> Path:
        return self.ensure_root() / self.TRADES_FILE

    def equity_timeseries_path(self) -> Path:
        return self.ensure_root() / self.EQUITY_TIMESERIES_FILE

    def strategy_summary_path(self) -> Path:
        return self.ensure_root() / self.STRATEGY_SUMMARY_FILE

    def metadata_path(self) -> Path:
        return self.ensure_root() / self.METADATA_FILE

    def stock_json_path(self, stock_id: str) -> Path:
        return self.ensure_root() / f"{stock_id}.json"


__all__ = ["ResultPathManager"]
