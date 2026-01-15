#!/usr/bin/env python3
"""
StatisticalAnalyzer - 统计学分析器

职责：
- 基于模拟器结果进行描述性统计分析
- 支持多种统计指标（通过枚举类管理）
- 使用 pandas + numpy 实现各类统计计算
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List
import json
import logging

import pandas as pd
import numpy as np

from .base_analyzer import BaseAnalyzer, AnalysisContext


logger = logging.getLogger(__name__)


class StatisticalMetric(str, Enum):
    """统计学分析可用指标枚举（白名单）。"""

    WIN_RATE_DISTRIBUTION = "win_rate_distribution"
    PNL_DISTRIBUTION = "pnl_distribution"
    MONTHLY_PERFORMANCE = "monthly_performance"
    YEARLY_PERFORMANCE = "yearly_performance"
    MAX_DRAWDOWN = "max_drawdown"
    HOLDING_PERIOD_BUCKET = "holding_period_bucket"


@dataclass
class StatisticalAnalyzer(BaseAnalyzer):
    """
    统计学分析器。

    从模拟器结果文件中读取数据，计算各类描述性统计指标。
    """

    metrics: List[str]  # 用户选择的指标列表（字符串形式）

    def __post_init__(self) -> None:
        """初始化后，将字符串 metrics 转换为枚举并验证。"""
        self._validated_metrics: List[StatisticalMetric] = []
        for metric_str in self.metrics:
            try:
                metric = StatisticalMetric(metric_str)
                self._validated_metrics.append(metric)
            except ValueError:
                logger.warning(
                    "[StatisticalAnalyzer] 未知指标 '%s'，已跳过", metric_str
                )

    def run(self) -> Dict[str, Any]:
        """
        执行统计学分析。

        Returns:
            包含所有选中指标的分析报告字典
        """
        report: Dict[str, Any] = {
            "strategy_name": self.context.strategy_name,
            "sim_type": self.context.sim_type,
            "sim_version_dir": str(self.context.sim_version_dir),
            "metrics": {},
        }

        # 加载数据
        df = self._load_data()
        if df is None or df.empty:
            logger.warning("[StatisticalAnalyzer] 无法加载数据或数据为空")
            return report

        # 按指标计算
        for metric in self._validated_metrics:
            try:
                if metric is StatisticalMetric.WIN_RATE_DISTRIBUTION:
                    report["metrics"]["win_rate_distribution"] = (
                        self._calc_win_rate_distribution(df)
                    )
                elif metric is StatisticalMetric.PNL_DISTRIBUTION:
                    report["metrics"]["pnl_distribution"] = self._calc_pnl_distribution(
                        df
                    )
                elif metric is StatisticalMetric.MONTHLY_PERFORMANCE:
                    report["metrics"]["monthly_performance"] = (
                        self._calc_monthly_performance(df)
                    )
                elif metric is StatisticalMetric.YEARLY_PERFORMANCE:
                    report["metrics"]["yearly_performance"] = (
                        self._calc_yearly_performance(df)
                    )
                elif metric is StatisticalMetric.MAX_DRAWDOWN:
                    report["metrics"]["max_drawdown"] = self._calc_max_drawdown(df)
                elif metric is StatisticalMetric.HOLDING_PERIOD_BUCKET:
                    report["metrics"]["holding_period_bucket"] = (
                        self._calc_holding_period_bucket(df)
                    )
            except Exception as exc:
                logger.warning(
                    "[StatisticalAnalyzer] 计算指标 %s 失败: %s", metric.value, exc
                )

        return report

    def _load_data(self) -> pd.DataFrame | None:
        """
        从模拟器结果文件加载数据为 DataFrame。

        根据 sim_type 选择不同的加载逻辑：
        - price_factor: 从 {stock_id}.json 加载 investments
        - capital_allocation: 从 trades.json 加载 trades

        Returns:
            DataFrame，包含投资/交易记录
        """
        sim_version_dir = self.context.sim_version_dir

        if self.context.sim_type == "price_factor":
            return self._load_price_factor_data(sim_version_dir)
        elif self.context.sim_type == "capital_allocation":
            return self._load_capital_allocation_data(sim_version_dir)
        else:
            logger.warning(
                "[StatisticalAnalyzer] 不支持的 sim_type: %s", self.context.sim_type
            )
            return None

    def _load_price_factor_data(self, sim_version_dir: Path) -> pd.DataFrame | None:
        """从 PriceFactorSimulator 结果加载数据。"""
        records: List[Dict[str, Any]] = []

        # 遍历所有 {stock_id}.json 文件
        for json_file in sim_version_dir.glob("*.json"):
            if json_file.name in ["0_session_summary.json", "0_metadata.json"]:
                continue

            try:
                with json_file.open("r", encoding="utf-8") as f:
                    stock_data = json.load(f)

                investments = stock_data.get("investments", [])
                for inv in investments:
                    # 提取关键字段
                    records.append(
                        {
                            "stock_id": stock_data.get("stock", {}).get("id", ""),
                            "start_date": inv.get("start_date", ""),
                            "end_date": inv.get("end_date", ""),
                            "roi": inv.get("roi", 0.0),
                            "profit": inv.get("overall_profit", 0.0),
                            "duration_days": inv.get("duration_in_days", 0),
                            "result": inv.get("result", ""),  # win/loss/open
                        }
                    )
            except Exception as exc:
                logger.warning(
                    "[StatisticalAnalyzer] 加载文件 %s 失败: %s", json_file, exc
                )

        if not records:
            return None

        df = pd.DataFrame(records)
        # 转换日期列
        if "start_date" in df.columns:
            df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
        if "end_date" in df.columns:
            df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")

        return df

    def _load_capital_allocation_data(
        self, sim_version_dir: Path
    ) -> pd.DataFrame | None:
        """从 CapitalAllocationSimulator 结果加载数据。"""
        trades_path = sim_version_dir / "trades.json"
        if not trades_path.exists():
            logger.warning(
                "[StatisticalAnalyzer] 未找到 trades.json: %s", trades_path
            )
            return None

        try:
            with trades_path.open("r", encoding="utf-8") as f:
                trades = json.load(f)

            if not trades:
                return None

            df = pd.DataFrame(trades)
            # 转换日期列
            if "buy_date" in df.columns:
                df["buy_date"] = pd.to_datetime(df["buy_date"], errors="coerce")
            if "sell_date" in df.columns:
                df["sell_date"] = pd.to_datetime(df["sell_date"], errors="coerce")

            # 标准化字段名（与 price_factor 对齐）
            if "realized_pnl" in df.columns:
                df["profit"] = df["realized_pnl"]
            if "roi" in df.columns:
                pass  # 已有
            else:
                # 计算 ROI
                df["roi"] = df.apply(
                    lambda row: (
                        (row.get("sell_price", 0) - row.get("buy_price", 0))
                        / row.get("buy_price", 1)
                        if row.get("buy_price", 0) > 0
                        else 0.0
                    ),
                    axis=1,
                )

            return df
        except Exception as exc:
            logger.warning(
                "[StatisticalAnalyzer] 加载 trades.json 失败: %s", exc
            )
            return None

    def _calc_win_rate_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算胜率分布（按 ROI 分桶）。"""
        if "roi" not in df.columns:
            return {}

        # 定义 ROI 分桶
        bins = [-np.inf, -0.5, -0.2, 0, 0.1, 0.3, np.inf]
        labels = ["<-50%", "-50%~-20%", "-20%~0%", "0%~10%", "10%~30%", ">=30%"]

        df["roi_bucket"] = pd.cut(df["roi"], bins=bins, labels=labels)

        # 计算每个桶的胜率
        bucket_stats = []
        for bucket in labels:
            bucket_df = df[df["roi_bucket"] == bucket]
            if bucket_df.empty:
                continue

            total = len(bucket_df)
            wins = len(bucket_df[bucket_df["roi"] > 0])
            win_rate = wins / total if total > 0 else 0.0

            bucket_stats.append(
                {
                    "bucket": bucket,
                    "total_count": total,
                    "win_count": wins,
                    "win_rate": round(win_rate, 4),
                    "avg_roi": round(bucket_df["roi"].mean(), 4),
                }
            )

        return {"buckets": bucket_stats}

    def _calc_pnl_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算盈亏分布（直方图数据）。"""
        if "roi" not in df.columns:
            return {}

        roi_values = df["roi"].dropna().tolist()

        # 计算直方图
        hist, bin_edges = np.histogram(roi_values, bins=20)

        return {
            "histogram": {
                "counts": hist.tolist(),
                "bin_edges": bin_edges.tolist(),
            },
            "statistics": {
                "min": float(df["roi"].min()),
                "max": float(df["roi"].max()),
                "mean": float(df["roi"].mean()),
                "median": float(df["roi"].median()),
                "std": float(df["roi"].std()),
            },
        }

    def _calc_monthly_performance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算月度表现。"""
        date_col = "start_date" if "start_date" in df.columns else "buy_date"
        if date_col not in df.columns:
            return {}

        df["year_month"] = df[date_col].dt.to_period("M")

        monthly_stats = []
        for period, group in df.groupby("year_month"):
            total = len(group)
            wins = len(group[group["roi"] > 0])
            win_rate = wins / total if total > 0 else 0.0

            monthly_stats.append(
                {
                    "period": str(period),
                    "total_trades": total,
                    "win_rate": round(win_rate, 4),
                    "avg_roi": round(group["roi"].mean(), 4),
                    "total_profit": round(group["profit"].sum(), 2),
                }
            )

        return {"monthly_stats": monthly_stats}

    def _calc_yearly_performance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算年度表现。"""
        date_col = "start_date" if "start_date" in df.columns else "buy_date"
        if date_col not in df.columns:
            return {}

        df["year"] = df[date_col].dt.year

        yearly_stats = []
        for year, group in df.groupby("year"):
            total = len(group)
            wins = len(group[group["roi"] > 0])
            win_rate = wins / total if total > 0 else 0.0

            # 计算最大回撤（简化版：该年度内的最大连续亏损）
            cumulative_roi = group["roi"].cumsum()
            running_max = cumulative_roi.expanding().max()
            drawdown = cumulative_roi - running_max
            max_drawdown = drawdown.min()

            yearly_stats.append(
                {
                    "year": int(year),
                    "total_trades": total,
                    "win_rate": round(win_rate, 4),
                    "avg_roi": round(group["roi"].mean(), 4),
                    "total_profit": round(group["profit"].sum(), 2),
                    "max_drawdown": round(max_drawdown, 4),
                }
            )

        return {"yearly_stats": yearly_stats}

    def _calc_max_drawdown(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算最大回撤。"""
        date_col = "start_date" if "start_date" in df.columns else "buy_date"
        if date_col not in df.columns or "roi" not in df.columns:
            return {}

        # 按日期排序
        df_sorted = df.sort_values(date_col)

        # 计算累计 ROI
        cumulative_roi = df_sorted["roi"].cumsum()
        running_max = cumulative_roi.expanding().max()
        drawdown = cumulative_roi - running_max
        max_dd = drawdown.min()
        max_dd_idx = drawdown.idxmin()

        return {
            "max_drawdown": round(float(max_dd), 4),
            "max_drawdown_date": str(df_sorted.loc[max_dd_idx, date_col])
            if max_dd_idx is not None
            else "",
        }

    def _calc_holding_period_bucket(self, df: pd.DataFrame) -> Dict[str, Any]:
        """按持仓天数分桶统计。"""
        duration_col = (
            "duration_days" if "duration_days" in df.columns else "holding_days"
        )
        if duration_col not in df.columns:
            return {}

        # 定义持仓天数分桶
        bins = [0, 5, 10, 20, 30, 60, np.inf]
        labels = ["0-5天", "5-10天", "10-20天", "20-30天", "30-60天", ">60天"]

        df["holding_bucket"] = pd.cut(df[duration_col], bins=bins, labels=labels)

        bucket_stats = []
        for bucket in labels:
            bucket_df = df[df["holding_bucket"] == bucket]
            if bucket_df.empty:
                continue

            total = len(bucket_df)
            wins = len(bucket_df[bucket_df["roi"] > 0])
            win_rate = wins / total if total > 0 else 0.0

            bucket_stats.append(
                {
                    "bucket": bucket,
                    "total_count": total,
                    "win_rate": round(win_rate, 4),
                    "avg_roi": round(bucket_df["roi"].mean(), 4),
                }
            )

        return {"buckets": bucket_stats}
