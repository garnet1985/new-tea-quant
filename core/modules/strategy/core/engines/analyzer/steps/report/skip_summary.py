"""Price-layer skip reason rollup for report step."""
from __future__ import annotations

from typing import Any, Dict


class PriceSkipSummary:
    @classmethod
    def build(cls, source: Dict[str, Any]) -> Dict[str, Any]:
        by_reason: Dict[str, int] = {}
        total = 0
        skipped = 0
        for entity in source.get("entities") or []:
            if not isinstance(entity, dict):
                continue
            for investment in entity.get("investments") or []:
                if not isinstance(investment, dict):
                    continue
                total += 1
                engine = investment.get("engine")
                if not isinstance(engine, dict):
                    continue
                reason = str(engine.get("skip_reason") or "").strip()
                if not reason:
                    continue
                skipped += 1
                by_reason[reason] = int(by_reason.get(reason) or 0) + 1
        return {
            "investment_count": total,
            "skipped_count": skipped,
            "by_reason": dict(sorted(by_reason.items())),
        }
