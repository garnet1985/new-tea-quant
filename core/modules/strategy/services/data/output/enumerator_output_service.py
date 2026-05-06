#!/usr/bin/env python3
"""Output writing helpers for enumerator artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import json

from core.modules.strategy.services.runtime.run_types import (
    StrategyRunFingerprint,
)

# 与 ``0_metadata.json`` 分列：大 universe 下不把数万 ``stock_ids`` 塞进主元数据 JSON。
SCOPE_STOCK_IDS_FILENAME = "0_scope_stock_ids.txt"


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
                    }
                )
            row = {k: v for k, v in opportunity.items() if k not in excluded}
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
    def write_fingerprint(
        *,
        output_dir: Path,
        fingerprint_payload: Dict[str, Any],
    ) -> None:
        with (output_dir / "0_fingerprint.json").open("w", encoding="utf-8") as f:
            json.dump(fingerprint_payload, f, indent=2, ensure_ascii=False)

    @staticmethod
    def fingerprint_dict_for_metadata(
        fingerprint: StrategyRunFingerprint,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """嵌入 ``0_metadata.json`` 的 fingerprint 去掉 ``stock_ids``；返回侧载文件用列表。"""
        d = fingerprint.to_dict()
        raw_ids = d.pop("stock_ids", None) or []
        scope_ids = sorted({str(x).strip() for x in raw_ids if str(x).strip()})
        if scope_ids:
            d["stock_ids_ref"] = SCOPE_STOCK_IDS_FILENAME
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
        优先读侧载 ``0_scope_stock_ids.txt``；否则回退旧版 ``0_metadata.json`` 内嵌 ``stock_ids``。
        均无则返回空列表。
        """
        sidecar = output_dir / SCOPE_STOCK_IDS_FILENAME
        if sidecar.is_file():
            try:
                lines = sidecar.read_text(encoding="utf-8").splitlines()
                ids = sorted({ln.strip() for ln in lines if ln.strip()})
                if ids:
                    return list(ids)
            except Exception:
                pass
        meta_path = output_dir / "0_metadata.json"
        if not meta_path.is_file():
            return []
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            fp = meta.get("fingerprint") if isinstance(meta, dict) else None
            raw = fp.get("stock_ids") if isinstance(fp, dict) else None
            if isinstance(raw, list) and raw:
                return sorted({str(s).strip() for s in raw if str(s).strip()})
        except Exception:
            pass
        return []

    @staticmethod
    def build_metadata(
        *,
        strategy_name: str,
        start_date: str,
        end_date: str,
        opportunity_count: int,
        version_id: int,
        version_dir_name: str,
        settings_snapshot: Dict[str, Any],
        is_full_enumeration: bool,
        fingerprint: StrategyRunFingerprint,
        status: str = "completed",
        created_at: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], List[str]]:
        fp_meta, scope_stock_ids = EnumeratorOutputWriterService.fingerprint_dict_for_metadata(
            fingerprint
        )
        metadata = {
            "strategy_name": strategy_name,
            "start_date": start_date,
            "end_date": end_date,
            "opportunity_count": opportunity_count,
            "created_at": created_at,
            "version_id": version_id,
            "version_dir": version_dir_name,
            "settings_snapshot": settings_snapshot,
            "is_full_enumeration": is_full_enumeration,
            "fingerprint": fp_meta,
            "status": status,
        }
        return metadata, scope_stock_ids


__all__ = ["EnumeratorOutputWriterService", "SCOPE_STOCK_IDS_FILENAME"]
