#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List
import json
import logging

import numpy as np
import pandas as pd

from .base import BaseAnalyzer

logger = logging.getLogger(__name__)


class StatisticalMetric(str, Enum):
    WIN_RATE_DISTRIBUTION = "win_rate_distribution"
    PNL_DISTRIBUTION = "pnl_distribution"
    MONTHLY_PERFORMANCE = "monthly_performance"
    YEARLY_PERFORMANCE = "yearly_performance"
    MAX_DRAWDOWN = "max_drawdown"
    HOLDING_PERIOD_BUCKET = "holding_period_bucket"


@dataclass
class StatisticalAnalyzer(BaseAnalyzer):
    metrics: List[str]

    def __post_init__(self) -> None:
        self._validated_metrics: List[StatisticalMetric] = []
        for metric_str in self.metrics:
            try:
                self._validated_metrics.append(StatisticalMetric(metric_str))
            except ValueError:
                logger.warning("[StatisticalAnalyzer] Unknown metric: %s", metric_str)

    def run(self) -> Dict[str, Any]:
        report: Dict[str, Any] = {
            "strategy_name": self.context.strategy_name,
            "sim_type": self.context.sim_type,
            "sim_version_dir": str(self.context.sim_version_dir),
            "metrics": {},
        }
        df = self._load_data()
        if df is None or df.empty:
            return report
        for metric in self._validated_metrics:
            if metric is StatisticalMetric.WIN_RATE_DISTRIBUTION:
                report["metrics"]["win_rate_distribution"] = self._calc_win_rate_distribution(df)
            elif metric is StatisticalMetric.PNL_DISTRIBUTION:
                report["metrics"]["pnl_distribution"] = self._calc_pnl_distribution(df)
            elif metric is StatisticalMetric.MONTHLY_PERFORMANCE:
                report["metrics"]["monthly_performance"] = self._calc_monthly_performance(df)
            elif metric is StatisticalMetric.YEARLY_PERFORMANCE:
                report["metrics"]["yearly_performance"] = self._calc_yearly_performance(df)
            elif metric is StatisticalMetric.MAX_DRAWDOWN:
                report["metrics"]["max_drawdown"] = self._calc_max_drawdown(df)
            elif metric is StatisticalMetric.HOLDING_PERIOD_BUCKET:
                report["metrics"]["holding_period_bucket"] = self._calc_holding_period_bucket(df)
        return report

    def _load_data(self) -> pd.DataFrame | None:
        if self.context.sim_type == "price_factor":
            return self._load_price_factor_data(self.context.sim_version_dir)
        if self.context.sim_type == "capital_allocation":
            return self._load_capital_allocation_data(self.context.sim_version_dir)
        return None

    def _load_price_factor_data(self, sim_version_dir: Path) -> pd.DataFrame | None:
        records: List[Dict[str, Any]] = []
        for json_file in sim_version_dir.glob("*.json"):
            if json_file.name in ["0_session_summary.json", "0_metadata.json", "0_performance_report.json"]:
                continue
            try:
                with json_file.open("r", encoding="utf-8") as f:
                    stock_data = json.load(f)
                for inv in stock_data.get("investments", []):
                    records.append(
                        {
                            "stock_id": stock_data.get("stock", {}).get("id", ""),
                            "start_date": inv.get("start_date", ""),
                            "end_date": inv.get("end_date", ""),
                            "roi": inv.get("roi", 0.0),
                            "profit": inv.get("overall_profit", 0.0),
                            "duration_days": inv.get("duration_in_days", 0),
                            "result": inv.get("result", ""),
                        }
                    )
            except Exception:
                continue
        if not records:
            return None
        df = pd.DataFrame(records)
        if "start_date" in df.columns:
            df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
        if "end_date" in df.columns:
            df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
        return df

    def _load_capital_allocation_data(self, sim_version_dir: Path) -> pd.DataFrame | None:
        trades_path = sim_version_dir / "trades.json"
        if not trades_path.exists():
            return None
        with trades_path.open("r", encoding="utf-8") as f:
            trades = json.load(f)
        if not trades:
            return None
        df = pd.DataFrame(trades)
        if "buy_date" in df.columns:
            df["buy_date"] = pd.to_datetime(df["buy_date"], errors="coerce")
        if "sell_date" in df.columns:
            df["sell_date"] = pd.to_datetime(df["sell_date"], errors="coerce")
        if "realized_pnl" in df.columns:
            df["profit"] = df["realized_pnl"]
        if "roi" not in df.columns:
            df["roi"] = df.apply(
                lambda row: ((row.get("sell_price", 0) - row.get("buy_price", 0)) / row.get("buy_price", 1))
                if row.get("buy_price", 0) > 0
                else 0.0,
                axis=1,
            )
        return df

    def _calc_win_rate_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        if "roi" not in df.columns:
            return {}
        bins = [-np.inf, -0.5, -0.2, 0, 0.1, 0.3, np.inf]
        labels = ["<-50%", "-50%~-20%", "-20%~0%", "0%~10%", "10%~30%", ">=30%"]
        df = df.copy()
        df["roi_bucket"] = pd.cut(df["roi"], bins=bins, labels=labels)
        bucket_stats = []
        for bucket in labels:
            bucket_df = df[df["roi_bucket"] == bucket]
            if bucket_df.empty:
                continue
            total = len(bucket_df)
            wins = len(bucket_df[bucket_df["roi"] > 0])
            bucket_stats.append(
                {
                    "bucket": bucket,
                    "total_count": total,
                    "win_count": wins,
                    "win_rate": round(wins / total if total > 0 else 0.0, 4),
                    "avg_roi": round(bucket_df["roi"].mean(), 4),
                }
            )
        return {"buckets": bucket_stats}

    def _calc_pnl_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        if "roi" not in df.columns:
            return {}
        roi_values = df["roi"].dropna().tolist()
        hist, bin_edges = np.histogram(roi_values, bins=20)
        return {
            "histogram": {"counts": hist.tolist(), "bin_edges": bin_edges.tolist()},
            "statistics": {
                "min": float(df["roi"].min()),
                "max": float(df["roi"].max()),
                "mean": float(df["roi"].mean()),
                "median": float(df["roi"].median()),
                "std": float(df["roi"].std()),
            },
        }

    def _calc_monthly_performance(self, df: pd.DataFrame) -> Dict[str, Any]:
        date_col = "start_date" if "start_date" in df.columns else "buy_date"
        if date_col not in df.columns:
            return {}
        df = df.copy()
        df["year_month"] = df[date_col].dt.to_period("M")
        monthly_stats = []
        for period, group in df.groupby("year_month"):
            total = len(group)
            wins = len(group[group["roi"] > 0])
            monthly_stats.append(
                {
                    "period": str(period),
                    "total_trades": total,
                    "win_rate": round(wins / total if total > 0 else 0.0, 4),
                    "avg_roi": round(group["roi"].mean(), 4),
                    "total_profit": round(group["profit"].sum(), 2),
                }
            )
        return {"monthly_stats": monthly_stats}

    def _calc_yearly_performance(self, df: pd.DataFrame) -> Dict[str, Any]:
        date_col = "start_date" if "start_date" in df.columns else "buy_date"
        if date_col not in df.columns:
            return {}
        df = df.copy()
        df["year"] = df[date_col].dt.year
        yearly_stats = []
        for year, group in df.groupby("year"):
            total = len(group)
            wins = len(group[group["roi"] > 0])
            cumulative_roi = group["roi"].cumsum()
            running_max = cumulative_roi.expanding().max()
            drawdown = cumulative_roi - running_max
            yearly_stats.append(
                {
                    "year": int(year),
                    "total_trades": total,
                    "win_rate": round(wins / total if total > 0 else 0.0, 4),
                    "avg_roi": round(group["roi"].mean(), 4),
                    "total_profit": round(group["profit"].sum(), 2),
                    "max_drawdown": round(drawdown.min(), 4),
                }
            )
        return {"yearly_stats": yearly_stats}

    def _calc_max_drawdown(self, df: pd.DataFrame) -> Dict[str, Any]:
        date_col = "start_date" if "start_date" in df.columns else "buy_date"
        if date_col not in df.columns or "roi" not in df.columns:
            return {}
        df_sorted = df.sort_values(date_col)
        cumulative_roi = df_sorted["roi"].cumsum()
        running_max = cumulative_roi.expanding().max()
        drawdown = cumulative_roi - running_max
        max_dd_idx = drawdown.idxmin()
        return {
            "max_drawdown": round(float(drawdown.min()), 4),
            "max_drawdown_date": str(df_sorted.loc[max_dd_idx, date_col]) if max_dd_idx is not None else "",
        }

    def _calc_holding_period_bucket(self, df: pd.DataFrame) -> Dict[str, Any]:
        duration_col = "duration_days" if "duration_days" in df.columns else "holding_days"
        if duration_col not in df.columns:
            return {}
        bins = [0, 5, 10, 20, 30, 60, np.inf]
        labels = ["0-5d", "5-10d", "10-20d", "20-30d", "30-60d", ">60d"]
        df = df.copy()
        df["holding_bucket"] = pd.cut(df[duration_col], bins=bins, labels=labels)
        bucket_stats = []
        for bucket in labels:
            bucket_df = df[df["holding_bucket"] == bucket]
            if bucket_df.empty:
                continue
            total = len(bucket_df)
            wins = len(bucket_df[bucket_df["roi"] > 0])
            bucket_stats.append(
                {
                    "bucket": bucket,
                    "total_count": total,
                    "win_rate": round(wins / total if total > 0 else 0.0, 4),
                    "avg_roi": round(bucket_df["roi"].mean(), 4),
                }
            )
        return {"buckets": bucket_stats}


__all__ = ["StatisticalMetric", "StatisticalAnalyzer"]
