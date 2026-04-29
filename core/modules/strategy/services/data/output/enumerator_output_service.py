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
