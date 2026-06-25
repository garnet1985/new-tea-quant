#!/usr/bin/env python3
"""Output writing helpers for enumerator artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import json

from core.modules.strategy.engines.shared.helpers.skip_investment_when import (
    stock_status_tags_csv_value,
)
from core.modules.strategy.launcher.run_types import (
    StrategyRunFingerprint,
)

# 侧载股票列表（旧版）；新跑次用 ``0_stock_ref.json`` 的键作为 universe。
SCOPE_STOCK_IDS_FILENAME = "0_scope_stock_ids.txt"
# 逐股摘要（ref）：``{ 代码: { stock_name, opportunities, completion_rate, avg_opportunity_interval_days } }``
STOCK_REF_FILENAME = "0_stock_ref.json"
class EnumeratorOutputWriterService:
    @staticmethod
    def build_stock_rows(
        *,
        opportunities: list[Dict[str, Any]],
        excluded_fields: Optional[set[str]] = None,
    ) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
        excluded = excluded_fields or {
            "completed_targets",
            "config_hash",
            "created_at",
            "updated_at",
            "record_of_today",
            "dynamic_loss_active",
            "dynamic_loss_highest",
            "expired_reason",
            "expired_date",
            "exit_reason",
            "protect_loss_active",
            "scan_date",
            "stock",
            "stock_id",
            "stock_name",
            "strategy_name",
            "strategy_version",
            "holding_days",
            "max_drawdown",
            "metadata",
            "price_return",
            "tracking",
            "triggered_stop_loss_idx",
        }
        opportunity_rows: list[Dict[str, Any]] = []
        target_rows: list[Dict[str, Any]] = []
        for opportunity in opportunities:
            completed_targets = opportunity.get("completed_targets", [])
            for target in completed_targets or []:
                target_rows.append(
                    {
                        "opportunity_id": opportunity.get("opportunity_id", ""),
                        "date": target.get("date", ""),
                        "sell_price": target.get("price", ""),
                        "sell_ratio": target.get("sell_ratio", ""),
                        "profit": target.get("profit", ""),
                        "weighted_profit": target.get("weighted_profit", ""),
                        "reason": target.get("reason", ""),
                        "roi": target.get("roi", ""),
                        "sell_prev_close": target.get("sell_prev_close", ""),
                        "sell_at_limit_down": target.get("sell_at_limit_down", ""),
                        "sell_bar_volume": target.get("sell_bar_volume", ""),
                    }
                )
            row = {k: v for k, v in opportunity.items() if k not in excluded}
            row["stock_status_at_trigger"] = stock_status_tags_csv_value(opportunity)
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    row[key] = json.dumps(value, ensure_ascii=False)
                elif value is None:
                    row[key] = ""
            opportunity_rows.append(row)
        return opportunity_rows, target_rows

    @staticmethod
    def write_stock_csv(
        *,
        output_dir: Path,
        stock_id: str,
        opportunity_rows: list[Dict[str, Any]],
        target_rows: list[Dict[str, Any]],
    ) -> None:
        from core.utils.io.csv_io import write_dicts_to_csv

        output_dir.mkdir(parents=True, exist_ok=True)
        if opportunity_rows:
            write_dicts_to_csv(
                output_dir / f"{stock_id}_opportunities.csv",
                opportunity_rows,
                preferred_order=list(opportunity_rows[0].keys()),
            )
        if target_rows:
            write_dicts_to_csv(
                output_dir / f"{stock_id}_targets.csv",
                target_rows,
                preferred_order=list(target_rows[0].keys()),
            )

    @staticmethod
    def write_performance_report(
        *,
        output_dir: Path,
        performance_summary: Dict[str, Any],
    ) -> None:
        with (output_dir / "0_performance_report.json").open("w", encoding="utf-8") as f:
            json.dump(performance_summary, f, indent=2, ensure_ascii=False)

    @staticmethod
    def write_metadata(
        *,
        output_dir: Path,
        metadata: Dict[str, Any],
    ) -> None:
        with (output_dir / "0_metadata.json").open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    @staticmethod
    def write_stock_summary_by_stock_id(
        *,
        output_dir: Path,
        by_stock_id: Dict[str, Dict[str, Any]],
    ) -> None:
        """单文件、以股票代码为键；数据在 job 完成时已在内存中汇总，此处仅一次顺序写盘。
        
        仅写入存在对应机会数据文件且内容非空的股票，避免 UI 显示无法查看详情的股票。
        """
        if not by_stock_id:
            return
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 过滤：只保留存在机会数据文件且内容非空的股票
        valid_stocks: Dict[str, Dict[str, Any]] = {}
        for sid in sorted(by_stock_id.keys()):
            opportunity_file = output_dir / f"{sid}_opportunities.csv"
            if opportunity_file.is_file():
                # 检查文件内容是否非空（至少有表头和一行数据）
                try:
                    content = opportunity_file.read_text(encoding="utf-8")
                    lines = [line.strip() for line in content.split("\n") if line.strip()]
                    # 至少需要表头 + 一行数据
                    if len(lines) >= 2:
                        valid_stocks[sid] = by_stock_id[sid]
                except Exception:
                    continue
        
        if not valid_stocks:
            return
            
        path = output_dir / STOCK_REF_FILENAME
        path.write_text(
            json.dumps(valid_stocks, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def fingerprint_dict_for_metadata(
        fingerprint: StrategyRunFingerprint,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """嵌入 ``0_metadata.json`` 的 fingerprint 保留 ``stock_ids``（用于价格回测 env 指纹）。"""
        d = fingerprint.to_dict()
        raw_ids = d.get("stock_ids", None) or []
        scope_ids = sorted({str(x).strip() for x in raw_ids if str(x).strip()})
        # 保留 stock_ids，不再移除并指向 0_stock_ref.json
        return d, scope_ids

    @staticmethod
    def write_scope_stock_ids(output_dir: Path, stock_ids: Sequence[str]) -> None:
        """一行一只股票代码，UTF-8；与 DbCache / 价格因子读取约定一致。"""
        path = output_dir / SCOPE_STOCK_IDS_FILENAME
        normalized = sorted({str(s).strip() for s in stock_ids if str(s).strip()})
        output_dir.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for sid in normalized:
                f.write(sid + "\n")

    @staticmethod
    def read_scope_stock_ids(output_dir: Path) -> List[str]:
        """
        解析枚举目录的股票 universe：优先读取 ``0_metadata.json`` 内嵌 ``stock_ids``（所有股票），
        再尝试侧载 ``0_scope_stock_ids.txt``，最后回退 ``0_stock_ref.json``（有 opportunities 的股票）。
        """
        # 优先读取 0_metadata.json 中的所有股票列表（用于 env fingerprint）
        meta_path = output_dir / "0_metadata.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                fp = meta.get("fingerprint") if isinstance(meta, dict) else None
                raw = fp.get("stock_ids") if isinstance(fp, dict) else None
                if isinstance(raw, list) and raw:
                    ids = sorted({str(s).strip() for s in raw if str(s).strip()})
                    if ids:
                        return list(ids)
            except Exception:
                pass
        # 尝试读取侧载文件
        sidecar = output_dir / SCOPE_STOCK_IDS_FILENAME
        if sidecar.is_file():
            try:
                lines = sidecar.read_text(encoding="utf-8").splitlines()
                ids = sorted({ln.strip() for ln in lines if ln.strip()})
                if ids:
                    return list(ids)
            except Exception:
                pass
        # 最后回退 0_stock_ref.json（只包含有 opportunities 的股票）
        ref_path = output_dir / STOCK_REF_FILENAME
        if ref_path.is_file():
            try:
                data = json.loads(ref_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data:
                    ids = sorted({str(k).strip() for k in data.keys() if str(k).strip()})
                    if ids:
                        return list(ids)
            except Exception:
                pass
        return []

    @staticmethod
    def build_metadata(
        *,
        strategy_name: str,
        start_date: str,
        end_date: str,
        version_id: int,
        version_dir_name: str,
        settings_snapshot: Dict[str, Any],
        is_full_enumeration: bool,
        fingerprint: StrategyRunFingerprint,
        status: str = "completed",
        created_at: Optional[str] = None,
        simulation_effective: Optional[Dict[str, Any]] = None,
        backtest_period: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, Any], List[str]]:
        fp_meta, scope_stock_ids = EnumeratorOutputWriterService.fingerprint_dict_for_metadata(
            fingerprint
        )
        metadata = {
            "strategy_name": strategy_name,
            "start_date": start_date,
            "end_date": end_date,
            "created_at": created_at,
            "output_version_id": version_id,
            "enumerator_output_dir": version_dir_name,
            "settings_snapshot": settings_snapshot,
            "is_full_enumeration": is_full_enumeration,
            "fingerprint": fp_meta,
            "status": status,
        }
        if simulation_effective:
            metadata["simulation"] = simulation_effective
        if isinstance(backtest_period, dict) and backtest_period:
            metadata["backtest_period"] = dict(backtest_period)
        return metadata, scope_stock_ids


__all__ = [
    "EnumeratorOutputWriterService",
    "SCOPE_STOCK_IDS_FILENAME",
    "STOCK_REF_FILENAME",
]
