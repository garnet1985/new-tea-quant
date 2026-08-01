"""BFF ``result_report`` slot hydrate (disk body + path metadata).

Assembles UI metrics from engine ``OverallReport.to_ui_dict()``.
Consumers: ``helpers/workbench_snapshots``, ``routes/report``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    OVERALL_REPORT_FILE,
)

logger = logging.getLogger(__name__)

_METRICS_KEYS = ("enumMetrics", "priceMetrics", "capitalMetrics")


def enum_opportunity_count_from_slot(slot: Optional[Dict[str, Any]]) -> Optional[int]:
    if not isinstance(slot, dict) or not slot:
        return None
    for key in ("opportunities", "opportunities_count"):
        if key in slot and slot.get(key) is not None:
            try:
                return int(slot[key])
            except (TypeError, ValueError):
                pass
    em = slot.get("enumMetrics")
    if isinstance(em, dict) and em.get("totalOpportunities") is not None:
        try:
            return int(em["totalOpportunities"])
        except (TypeError, ValueError):
            return None
    return None


def attach_enum_opportunities_field(slot: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(slot, dict) or not slot:
        return slot
    out = dict(slot)
    count = enum_opportunity_count_from_slot(out)
    if count is not None:
        out["opportunities"] = count
    return out


def _slot_has_metrics(slot: Dict[str, Any], metrics_key: str) -> bool:
    inner = slot.get(metrics_key)
    return isinstance(inner, dict) and bool(inner)


def _merge_ui_into_slot(slot: Dict[str, Any], ui: Dict[str, Any]) -> Dict[str, Any]:
    """Prefer existing slot metrics; fill missing UI fields from disk ``to_ui_dict``."""
    out = dict(slot)
    for key, value in ui.items():
        if key in _METRICS_KEYS:
            if not _slot_has_metrics(out, key) and isinstance(value, dict) and value:
                out[key] = dict(value)
            continue
        if key == "backtest_period":
            if not out.get("backtest_period") and isinstance(value, dict) and value:
                out["backtest_period"] = dict(value)
            continue
        if key not in out or out.get(key) in (None, "", {}):
            out[key] = value
    return out


def _version_dir_candidates_from_slot(
    slot: Dict[str, Any], workbench_version: int = 0
) -> List[str]:
    dirs: List[str] = []

    out_d = str(slot.get("output_dir") or "").strip()
    if out_d:
        dirs.append(out_d)

    vid = slot.get("version_id")
    if vid is not None:
        try:
            dirs.append(str(int(vid)))
        except (TypeError, ValueError):
            text = str(vid).strip()
            if text:
                dirs.append(text)

    if workbench_version > 0:
        dirs.append(str(int(workbench_version)))

    seen: set[str] = set()
    uniq: List[str] = []
    for d in dirs:
        if d and d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq


def resolve_simulation_output_dirs(
    strategy_name: str,
    *,
    step: str,
    slot: Optional[Dict[str, Any]] = None,
    workbench_version: int = 0,
) -> List[Path]:
    """Absolute version-dir candidates for enum / price / portfolio."""
    sn = str(strategy_name or "").strip()
    if not sn:
        return []

    slot = slot if isinstance(slot, dict) else {}
    names = _version_dir_candidates_from_slot(slot, workbench_version)
    if step == "enum":
        root = ProjectContext.path.get_strategy_directory_simulation_enum(sn)
    elif step == "price":
        root = ProjectContext.path.get_strategy_directory_simulation_price(sn)
    elif step == "portfolio":
        root = ProjectContext.path.get_strategy_directory_simulation_portfolio(sn)
    else:
        return []

    out: List[Path] = []
    seen: set[str] = set()
    for name in names:
        p = Path(name)
        if not p.is_absolute():
            p = root / name
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _load_overall_ui(step: str, output_dir: Path) -> Optional[Dict[str, Any]]:
    path = output_dir / OVERALL_REPORT_FILE
    if not path.is_file():
        return None
    try:
        if step == "enum":
            from core.modules.strategy.core.engines.enumerator.common.report_manager.overall_report import (
                OverallReport,
            )
        elif step == "price":
            from core.modules.strategy.core.engines.price_factor.report_manager.overall_report import (
                OverallReport,
            )
        else:
            from core.modules.strategy.core.engines.portfolio.report_manager.overall_report import (
                OverallReport,
            )
        return OverallReport.load(output_dir).to_ui_dict()
    except Exception:
        logger.debug("failed to load overall_report from %s", output_dir, exc_info=True)
        return None


def hydrate_enum_slot(
    strategy_name: str,
    slot: Dict[str, Any],
    *,
    workbench_version: int = 0,
) -> Dict[str, Any]:
    if not isinstance(slot, dict) or not slot:
        return slot
    sn = str(strategy_name or "").strip()
    if not sn or _slot_has_metrics(slot, "enumMetrics"):
        return slot

    for output_dir in resolve_simulation_output_dirs(
        sn, step="enum", slot=slot, workbench_version=workbench_version
    ):
        ui = _load_overall_ui("enum", output_dir)
        if ui:
            return _merge_ui_into_slot(slot, ui)
    return slot


def hydrate_price_slot(
    strategy_name: str,
    slot: Dict[str, Any],
    *,
    workbench_version: int = 0,
) -> Dict[str, Any]:
    if not isinstance(slot, dict) or not slot:
        return slot
    sn = str(strategy_name or "").strip()
    if not sn or _slot_has_metrics(slot, "priceMetrics"):
        return slot

    for output_dir in resolve_simulation_output_dirs(
        sn, step="price", slot=slot, workbench_version=workbench_version
    ):
        ui = _load_overall_ui("price", output_dir)
        if ui:
            return _merge_ui_into_slot(slot, ui)
    return slot


def hydrate_portfolio_slot(
    strategy_name: str,
    slot: Dict[str, Any],
    *,
    workbench_version: int = 0,
) -> Dict[str, Any]:
    """Hydrate portfolio slot from ``overall_report.json`` when metrics missing."""
    if not isinstance(slot, dict) or not slot:
        return slot
    sn = str(strategy_name or "").strip()
    if not sn or _slot_has_metrics(slot, "capitalMetrics"):
        return slot

    for output_dir in resolve_simulation_output_dirs(
        sn, step="portfolio", slot=slot, workbench_version=workbench_version
    ):
        ui = _load_overall_ui("portfolio", output_dir)
        if ui:
            return _merge_ui_into_slot(slot, ui)
    return slot


def hydrate_workbench_result_report(
    strategy_name: str,
    result_report: Optional[Dict[str, Any]],
    *,
    workbench_version: int = 0,
) -> Dict[str, Any]:
    rr = dict(result_report or {})
    sn = str(strategy_name or "").strip()
    if not sn:
        return rr

    en = rr.get("enum")
    if isinstance(en, dict) and en:
        rr["enum"] = attach_enum_opportunities_field(
            hydrate_enum_slot(sn, en, workbench_version=workbench_version)
        )

    price = rr.get("price_factor")
    if isinstance(price, dict) and price:
        rr["price_factor"] = hydrate_price_slot(
            sn, price, workbench_version=workbench_version
        )

    portfolio = rr.get("portfolio")
    if isinstance(portfolio, dict) and portfolio:
        rr["portfolio"] = hydrate_portfolio_slot(
            sn, portfolio, workbench_version=workbench_version
        )
    return rr


__all__ = [
    "attach_enum_opportunities_field",
    "enum_opportunity_count_from_slot",
    "hydrate_enum_slot",
    "hydrate_price_slot",
    "hydrate_portfolio_slot",
    "hydrate_workbench_result_report",
    "resolve_simulation_output_dirs",
]
