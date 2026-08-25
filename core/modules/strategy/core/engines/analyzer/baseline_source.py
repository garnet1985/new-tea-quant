"""Load baseline attribution source for run comparison."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

from .collector import AttributionInputCollector
from .consts import ANALYSIS_SUBDIR, SOURCE_JSON


def load_baseline_source(
    strategy_folder: Union[str, Path],
    *,
    kind: SimulateKind,
    baseline_version_id: str,
) -> Dict[str, Any]:
    vid = str(baseline_version_id or "").strip()
    if not vid:
        raise ValueError("baseline_version_id 不能为空")

    baseline_store = ArtifactStore.resolve(strategy_folder, kind=kind, version_id=vid)
    source_path = Path(baseline_store.output_dir) / ANALYSIS_SUBDIR / SOURCE_JSON
    if source_path.is_file():
        payload = ArtifactIO.read_json(source_path)
        if isinstance(payload, dict):
            return payload

    baseline_store = ArtifactStore.open(
        baseline_store.output_dir,
        kind=kind,
        version_id=vid,
    )
    return AttributionInputCollector(baseline_store).collect()


__all__ = ["load_baseline_source"]
