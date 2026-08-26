"""Load attribution ``insights`` for BFF step report (via Strategy Facade)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def load_step_analysis(output_dir: Path) -> Dict[str, Any]:
    from core.modules.strategy import Strategy

    return Strategy.step_analysis_from_output_dir(output_dir)


def resolve_analysis_for_step(
    strategy_name: str,
    step: str,
    slot: Optional[Dict[str, Any]],
    *,
    workbench_version: int = 0,
) -> Dict[str, Any]:
    from core.modules.strategy import Strategy

    return Strategy.resolve_step_analysis(
        strategy_name,
        step,
        slot if isinstance(slot, dict) else {},
        workbench_version=int(workbench_version or 0),
    )


__all__ = ["load_step_analysis", "resolve_analysis_for_step"]
