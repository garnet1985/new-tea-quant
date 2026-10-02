"""把层诊断写到该步 ``attribution.json``。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from core.modules.strategy.core.engines.analyzer.steps.layer.consts import LAYER_SCHEMA
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore


class LayerPersist:
    """``{vid}/{enum|price|portfolio}/attribution.json``。"""

    @classmethod
    def run(
        cls,
        store: ArtifactStore,
        *,
        facts: Mapping[str, Any],
        conclusions: Sequence[Mapping[str, Any]],
        suggestions: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        payload = {
            "schema_version": LAYER_SCHEMA,
            "layer": _layer_name(store.kind),
            "version_id": str(store.version_id or ""),
            "disclaimer": str(facts.get("disclaimer") or ""),
            "facts": dict(facts),
            "conclusions": [dict(item) for item in conclusions],
            "suggestions": [dict(item) for item in suggestions],
        }
        path = store.write_json("layer_attribution", payload)
        payload["report_path"] = str(Path(path).resolve())
        payload["output_dir"] = str(store.output_dir.resolve())
        payload["success"] = True
        payload["skipped"] = False
        return payload


def layer_report_path(store: ArtifactStore) -> Path:
    return store.file("layer_attribution")


def load_layer_report(store: ArtifactStore) -> Optional[Dict[str, Any]]:
    path = layer_report_path(store)
    if not path.is_file():
        return None
    payload = store.read_json("layer_attribution")
    return payload if isinstance(payload, dict) else None


def _layer_name(kind: SimulateKind) -> str:
    if kind == SimulateKind.PRICE_FACTOR:
        return "price_factor"
    if kind == SimulateKind.PORTFOLIO:
        return "portfolio"
    return "enumerate"
