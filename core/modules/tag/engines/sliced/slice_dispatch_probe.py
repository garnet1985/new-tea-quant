"""Tag calendar_slice dispatch probe — run a small orchestrator sample."""
from __future__ import annotations

from typing import Any, Dict

__all__ = ["execute_tag_slice_probe_payload"]


def execute_tag_slice_probe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    from core.modules.tag.engines.sliced.worker import run_tag_calendar_slice_payload

    probe = dict(payload)
    probe["_slice_probe"] = True
    return run_tag_calendar_slice_payload(probe)
