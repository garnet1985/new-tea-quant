#!/usr/bin/env python3
"""
ResultPathManager - 统一结果目录与文件路径管理器

职责：
- 管理模拟器版本目录下的文件与子目录创建
- 为不同模拟器提供一致的结果文件命名约定
- 封装 Path 逻辑，避免在各个模拟器中重复拼接路径/调用 mkdir

当前支持：
- PriceFactorSimulator
- CapitalAllocationSimulator
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging


logger = logging.getLogger(__name__)


@dataclass
class ResultPathManager:
    """
    模拟器结果目录管理器

    约定目录结构（由 VersionManager 创建顶层版本目录）：

    app/userspace/strategies/{strategy_name}/results/
    ├── simulations/
    │   └── price_factor/{sim_version}/
    │       ├── 0_session_summary.json
    │       ├── metadata.json
    │       └── {stock_id}.json
    └── capital_allocation/{sim_version}/
            ├── trades.json
            ├── portfolio_timeseries.json
            ├── summary_strategy.json
            └── metadata.json
    """

    sim_version_dir: Path

    # 文件命名约定（会话级文件统一使用 0_ 前缀，方便排序）
    SESSION_SUMMARY_FILE: str = "0_session_summary.json"
    TRADES_FILE: str = "trades.json"
    EQUITY_TIMESERIES_FILE: str = "portfolio_timeseries.json"
    STRATEGY_SUMMARY_FILE: str = "summary_strategy.json"
    METADATA_FILE: str = "0_metadata.json"

    def ensure_root(self) -> Path:
        """
        确保模拟器版本目录存在并返回。
        VersionManager 通常已经创建了该目录，但这里再做一次幂等保证。
        """
        try:
            self.sim_version_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # 容错日志，避免因权限等问题无提示
            logger.warning(
                "[ResultPathManager] 创建结果目录失败: dir=%s, error=%s",
                self.sim_version_dir,
                exc,
            )
            # 继续抛出，让上层决定如何处理
            raise
        return self.sim_version_dir

    # --------------------------------------------------------------------- #
    # 通用结果文件路径
    # --------------------------------------------------------------------- #

    def session_summary_path(self) -> Path:
        """会话级 summary 文件路径（PriceFactorSimulator 使用）。"""
        root = self.ensure_root()
        return root / self.SESSION_SUMMARY_FILE

    def trades_path(self) -> Path:
        """交易记录文件路径（CapitalAllocationSimulator 使用）。"""
        root = self.ensure_root()
        return root / self.TRADES_FILE

    def equity_timeseries_path(self) -> Path:
        """组合权益时间序列文件路径（CapitalAllocationSimulator 使用）。"""
        root = self.ensure_root()
        return root / self.EQUITY_TIMESERIES_FILE

    def strategy_summary_path(self) -> Path:
        """策略整体汇总文件路径（CapitalAllocationSimulator 使用）。"""
        root = self.ensure_root()
        return root / self.STRATEGY_SUMMARY_FILE

    def metadata_path(self) -> Path:
        """metadata.json 路径（两个模拟器共用）。"""
        root = self.ensure_root()
        return root / self.METADATA_FILE

    # --------------------------------------------------------------------- #
    # 单股票结果文件路径（PriceFactorSimulator 使用）
    # --------------------------------------------------------------------- #

    def stock_json_path(self, stock_id: str) -> Path:
        """
        单只股票模拟结果 JSON 文件路径。

        命名规则保持现有实现：{stock_id}.json
        """
        root = self.ensure_root()
        return root / f"{stock_id}.json"

