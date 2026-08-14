"""Bundle manifest read/write."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..contracts import ArtifactSpec, BundleManifest, ManifestEntry


class BundleManifestIO:
    """manifest.json 读写与从 ArtifactSpec 构造。"""

    FILENAME = "manifest.json"
    SUPPORTED_FORMAT_VERSION = 1

    @staticmethod
    def from_specs(
        specs: List[ArtifactSpec],
        *,
        metadata: Optional[Dict[str, Any]] = None,
        exported_at: Optional[str] = None,
    ) -> BundleManifest:
        entries = [
            ManifestEntry(
                kind=spec.kind,
                name=spec.name,
                archive_prefix=spec.normalized_archive_prefix(),
                target_relative=spec.normalized_target_relative(),
            )
            for spec in specs
        ]
        ts = exported_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        return BundleManifest(
            format_version=BundleManifestIO.SUPPORTED_FORMAT_VERSION,
            entries=entries,
            exported_at=ts,
            metadata=dict(metadata or {}),
        )

    @staticmethod
    def validate(manifest: BundleManifest) -> None:
        if manifest.format_version != BundleManifestIO.SUPPORTED_FORMAT_VERSION:
            raise ValueError(
                f"unsupported manifest format_version={manifest.format_version}, "
                f"expected {BundleManifestIO.SUPPORTED_FORMAT_VERSION}"
            )
        if not manifest.entries:
            raise ValueError("manifest.entries must not be empty")
        seen_prefixes = set()
        for entry in manifest.entries:
            if not entry.kind or not entry.name:
                raise ValueError("manifest entry kind and name are required")
            if not entry.archive_prefix or not entry.target_relative:
                raise ValueError(
                    "manifest entry archive_prefix and target_relative are required"
                )
            if entry.archive_prefix in seen_prefixes:
                raise ValueError(
                    f"duplicate manifest archive_prefix: {entry.archive_prefix}"
                )
            seen_prefixes.add(entry.archive_prefix)

    @staticmethod
    def write(manifest: BundleManifest, dest_dir: Path) -> Path:
        BundleManifestIO.validate(manifest)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / BundleManifestIO.FILENAME
        path.write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def read(source: Union[Path, str]) -> BundleManifest:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"manifest not found: {path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("manifest root must be a JSON object")
        manifest = BundleManifest.from_dict(raw)
        BundleManifestIO.validate(manifest)
        return manifest
