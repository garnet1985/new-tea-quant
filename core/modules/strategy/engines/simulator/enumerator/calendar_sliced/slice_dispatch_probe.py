"""Strategy calendar_slice dispatch probe — run a small orchestrator sample."""
from __future__ import annotations

from typing import Any, Dict

__all__ = ["execute_enum_slice_probe_payload"]


def execute_enum_slice_probe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.worker import (
        run_calendar_slice_enumeration_payload,
    )

    probe = dict(payload)
    probe["_slice_probe"] = True
    return run_calendar_slice_enumeration_payload(probe)
