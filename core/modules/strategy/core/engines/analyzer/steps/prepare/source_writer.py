"""Write / read ``analysis/source.json`` (analyze-step input artifact)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

from ...support.paths import AnalyzerPaths


class SourceWriter:
    """Write / read ``analysis/source.json`` (prepare-step output, analyze-step input).

    Format note: nested JSON today; may split to manifest + flat CSV later.
    """

    @classmethod
    def write(
        cls,
        store: ArtifactStore,
        payload: Dict[str, Any],
        *,
        collected_at: Optional[str] = None,
    ) -> Path:
        body = dict(payload)
        body["collected_at"] = collected_at or datetime.now().isoformat()
        analysis_dir = Path(store.output_dir) / AnalyzerPaths.ANALYSIS_SUBDIR
        analysis_dir.mkdir(parents=True, exist_ok=True)
        source_path = analysis_dir / AnalyzerPaths.SOURCE_JSON
        ArtifactIO.write_json(source_path, body)
        return source_path

    @classmethod
    def read(cls, source_path: Path) -> Dict[str, Any]:
        payload = ArtifactIO.read_json(Path(source_path))
        if not isinstance(payload, dict):
            raise ValueError(f"invalid source.json: {source_path}")
        return payload
