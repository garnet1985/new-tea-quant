#!/usr/bin/env python3
"""Output writing helpers for enumerator artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import json

from core.modules.strategy.engines.simulator.enumerator.data_classes.fingerprint import (
    EnumeratorFingerprint,
)
from core.modules.strategy.enums import NotReusedBecause, ReuseAction


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
        fingerprint: EnumeratorFingerprint,
        status: str = "completed",
        reuse_action: Optional[ReuseAction] = None,
        not_reused_because: Optional[NotReusedBecause] = None,
        created_at: Optional[str] = None,
    ) -> Dict[str, Any]:
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
            "fingerprint": fingerprint.to_dict(),
            "status": status,
        }
        if reuse_action:
            metadata["reuse_action"] = reuse_action.value
        if not_reused_because and not_reused_because != NotReusedBecause.NONE:
            metadata["not_reused_because"] = not_reused_because.value
        return metadata


__all__ = ["EnumeratorOutputWriterService"]
