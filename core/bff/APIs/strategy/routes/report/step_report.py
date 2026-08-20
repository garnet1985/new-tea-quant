"""BFF step report builders (V2-07 / V2-07b).

Reads snapshot ``result_report`` slots + disk reports
(``overall_report.json`` / ``entity_list.json``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.data_manager import DataManager
from core.modules.strategy.core.services.artifacts import ArtifactStore, EnumerateStore, PriceFactorStore
from core.modules.strategy.contracts import WorkbenchStep
from core.bff.APIs.strategy.helpers.report_hydrate import (
    attach_enum_opportunities_field,
    hydrate_enum_slot,
    hydrate_portfolio_slot,
    hydrate_price_slot,
    resolve_simulation_output_dirs,
)
from core.bff.APIs.strategy.helpers.workbench_snapshots import WorkbenchSnapshots

logger = logging.getLogger(__name__)


class WorkbenchReports:
    """V2-07 step report + V2-07b per-stock ref."""

    @classmethod
    def build_step_report(
        cls,
        *,
        strategy_name: str,
        normalized_step: str,
        version: int,
    ) -> Optional[Dict[str, Any]]:
        """Read snapshot slot for step; missing row → ``None`` (route 404)."""
        step = WorkbenchStep.try_parse(normalized_step)
        if step is None:
            return None

        name = str(strategy_name).strip()
        row = WorkbenchSnapshots.fetch_by_version(name, int(version))
        if not row:
            return None

        report = cls._resolve_step_report(
            name,
            step,
            row,
            workbench_version=int(version),
        )
        return {
            "version_id": f"v{int(version)}",
            "strategy_name": name,
            "step": step.value,
            "report": report,
        }

    @classmethod
    def build_step_report_ref(
        cls,
        *,
        strategy_name: str,
        normalized_step: str,
        version: int,
    ) -> Optional[Dict[str, Any]]:
        """Load per-stock ref from ``entity_list.json`` (enum / price).

        Missing snapshot → ``None``. Missing disk file → ``stock_ref_available=False``.
        """
        if normalized_step not in (
            WorkbenchStep.ENUM.value,
            WorkbenchStep.PRICE.value,
        ):
            return None
        step = WorkbenchStep.parse(normalized_step)
        name = str(strategy_name).strip()
        if not name or version <= 0:
            return None

        row = WorkbenchSnapshots.fetch_by_version(name, int(version))
        if not row:
            return None

        rr = dict(row.get("result_report") or {})
        slot_key = step.report_slot
        slot = rr.get(slot_key) if isinstance(rr.get(slot_key), dict) else {}

        stock_ref: Optional[Dict[str, Any]] = None
        resolved_dir = ""

        for output_dir in resolve_simulation_output_dirs(
            name,
            step=step.value,
            slot=slot if isinstance(slot, dict) else {},
            workbench_version=int(version),
        ):
            if not output_dir.is_dir():
                continue
            loaded = cls._load_stock_ref_from_dir(step.value, output_dir)
            # ``{}`` is a valid empty grid (0 opportunities); only ``None`` means unavailable.
            if loaded is not None:
                stock_ref = loaded
                resolved_dir = output_dir.name
                break

        common = {
            "version_id": f"v{int(version)}",
            "strategy_name": name,
            "step": step.value,
        }
        if stock_ref is None:
            return {
                **common,
                "stock_ref": None,
                "stock_ref_available": False,
                "resolved_output_dir": "",
            }

        stock_ref = cls._enrich_stock_ref_with_list_names(stock_ref)
        return {
            **common,
            "stock_ref": stock_ref,
            "stock_ref_available": True,
            "resolved_output_dir": resolved_dir,
        }

    @classmethod
    def _resolve_step_report(
        cls,
        strategy_name: str,
        step: WorkbenchStep,
        row: Dict[str, Any],
        *,
        workbench_version: int,
    ) -> Dict[str, Any]:
        rr = dict(row.get("result_report") or {})
        raw = rr.get(step.report_slot)
        if not isinstance(raw, dict) or not raw:
            return {}

        if step is WorkbenchStep.ENUM:
            return attach_enum_opportunities_field(
                hydrate_enum_slot(
                    strategy_name, raw, workbench_version=workbench_version
                )
            )
        if step is WorkbenchStep.PRICE:
            return hydrate_price_slot(
                strategy_name, raw, workbench_version=workbench_version
            )
        return hydrate_portfolio_slot(
            strategy_name, raw, workbench_version=workbench_version
        )

    @classmethod
    def _load_stock_ref_from_dir(
        cls, step: str, output_dir: Path
    ) -> Optional[Dict[str, Any]]:
        try:
            kind = ArtifactStore.parse_kind(step)
        except ValueError:
            return None
        store = ArtifactStore.for_kind(kind).at(output_dir)
        entity_list = store.file("entity_list")
        if not entity_list.is_file():
            return None
        try:
            if step == "enum":
                from core.modules.strategy.core.engines.enumerator.common.report_manager.entity_list_report import (
                    EntityListReport,
                )

                raw = EntityListReport.load(output_dir).to_ui_dict()
                return cls._filter_enum_stock_ref(output_dir, raw)
            from core.modules.strategy.core.engines.price_factor.report_manager.entity_list_report import (
                EntityListReport,
            )

            raw = EntityListReport.load(output_dir).to_ui_dict()
            return cls._filter_price_stock_ref(output_dir, raw)
        except Exception:
            logger.debug(
                "failed to load entity_list from %s", output_dir, exc_info=True
            )
            return None

    @classmethod
    def _filter_enum_stock_ref(
        cls, output_dir: Path, raw: Dict[str, Any]
    ) -> Dict[str, Any]:
        valid: Dict[str, Any] = {}
        for sid, payload in raw.items():
            if not cls._enum_entity_has_data(output_dir, str(sid)):
                continue
            valid[str(sid)] = dict(payload) if isinstance(payload, dict) else payload
        return valid

    @classmethod
    def _filter_price_stock_ref(
        cls, output_dir: Path, raw: Dict[str, Any]
    ) -> Dict[str, Any]:
        valid: Dict[str, Any] = {}
        for sid, payload in raw.items():
            if not cls._price_entity_has_data(output_dir, str(sid)):
                continue
            valid[str(sid)] = dict(payload) if isinstance(payload, dict) else payload
        return valid

    @classmethod
    def _enum_entity_has_data(cls, output_dir: Path, entity_id: str) -> bool:
        eid = str(entity_id or "").strip()
        if not eid:
            return False
        store = EnumerateStore.at(output_dir)
        if not store.has_investments(eid):
            return False
        return bool(store.investments(eid).rows)

    @classmethod
    def _price_entity_has_data(cls, output_dir: Path, entity_id: str) -> bool:
        eid = str(entity_id or "").strip().replace("/", "_")
        if not eid:
            return False
        return PriceFactorStore.at(output_dir).has_investments(eid)

    @staticmethod
    def _batch_load_stock_display_names(codes: List[str]) -> Dict[str, str]:
        model = DataManager().get_table("sys_stock_list")
        if model is None or not codes:
            return {}
        out: Dict[str, str] = {}
        deduped = list(dict.fromkeys(c for c in codes if c))
        chunk_size = 500
        for i in range(0, len(deduped), chunk_size):
            chunk = deduped[i : i + chunk_size]
            ph = ",".join(["%s"] * len(chunk))
            try:
                rows = model.load(f"id IN ({ph})", tuple(chunk))
            except Exception:
                continue
            for r in rows or []:
                rec = dict(r or {})
                sid = str(rec.get("id") or "").strip()
                nm = str(rec.get("name") or "").strip()
                if sid and nm:
                    out[sid] = nm
        return out

    @classmethod
    def _enrich_stock_ref_with_list_names(
        cls, stock_ref: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not isinstance(stock_ref, dict) or not stock_ref:
            return stock_ref
        need: List[str] = []
        for sid, payload in stock_ref.items():
            code = str(sid).strip()
            if not code:
                continue
            row = payload if isinstance(payload, dict) else {}
            sn = str(row.get("stock_name") or "").strip()
            if not sn or sn == code:
                need.append(code)
        names = cls._batch_load_stock_display_names(need)
        if not names:
            return stock_ref
        out: Dict[str, Any] = {}
        for sid, payload in stock_ref.items():
            code = str(sid).strip()
            base = dict(payload) if isinstance(payload, dict) else {}
            sn = str(base.get("stock_name") or "").strip()
            if (not sn or sn == code) and code in names:
                base["stock_name"] = names[code]
            out[str(sid)] = base
        return out


__all__ = ["WorkbenchReports"]
