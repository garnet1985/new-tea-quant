"""Load baseline attribution source for run comparison."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore

from ..prepare import PrepareStep


class BaselineSourceLoader:
    @staticmethod
    def load(
        strategy_folder: Union[str, Path],
        *,
        kind: SimulateKind,
        baseline_version_id: str,
    ) -> Dict[str, Any]:
        vid = str(baseline_version_id or "").strip()
        if not vid:
            raise ValueError("baseline_version_id 不能为空")

        baseline_store = ArtifactStore.resolve(
            strategy_folder, kind=kind, version_id=vid
        )
        source_path = baseline_store.file("analysis_source")
        if source_path.is_file():
            return baseline_store.read_json("analysis_source")

        baseline_store = ArtifactStore.open(
            baseline_store.output_dir,
            kind=kind,
            version_id=vid,
        )
        return PrepareStep(baseline_store).build()
