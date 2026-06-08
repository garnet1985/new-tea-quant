"""Shared types for userspace bundle export/import."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConflictPolicy(str, Enum):
    """How to handle target paths that already exist on install."""

    REJECT = "reject"
    SKIP_EXISTING = "skip_existing"
    OVERWRITE = "overwrite"


@dataclass(frozen=True)
class ArtifactSpec:
    """
    One logical artifact to include in a bundle.

    Files under ``source_dir`` are archived under ``archive_prefix/`` and installed
    under ``userspace_root / target_relative /``.
    """

    kind: str
    name: str
    source_dir: Path
    archive_prefix: str
    target_relative: str

    def normalized_archive_prefix(self) -> str:
        return str(self.archive_prefix or "").strip().strip("/")

    def normalized_target_relative(self) -> str:
        return str(self.target_relative or "").strip().strip("/")


@dataclass(frozen=True)
class CollectedFile:
    """A single file entry inside a bundle payload."""

    archive_path: str
    source_path: Path


@dataclass
class ManifestEntry:
    kind: str
    name: str
    archive_prefix: str
    target_relative: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "archive_prefix": self.archive_prefix,
            "target_relative": self.target_relative,
        }

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> "ManifestEntry":
        return ManifestEntry(
            kind=str(raw.get("kind") or "").strip(),
            name=str(raw.get("name") or "").strip(),
            archive_prefix=str(raw.get("archive_prefix") or "").strip().strip("/"),
            target_relative=str(raw.get("target_relative") or "").strip().strip("/"),
        )


@dataclass
class BundleManifest:
    format_version: int
    entries: List[ManifestEntry]
    exported_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "format_version": int(self.format_version),
            "entries": [e.to_dict() for e in self.entries],
        }
        if self.exported_at:
            out["exported_at"] = self.exported_at
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> "BundleManifest":
        entries_raw = raw.get("entries") or []
        if not isinstance(entries_raw, list):
            raise ValueError("manifest.entries 必须为 list")
        return BundleManifest(
            format_version=int(raw.get("format_version") or 0),
            exported_at=str(raw.get("exported_at") or "").strip() or None,
            metadata=dict(raw.get("metadata") or {}) if isinstance(raw.get("metadata"), dict) else {},
            entries=[ManifestEntry.from_dict(x) for x in entries_raw if isinstance(x, dict)],
        )


@dataclass
class ConflictItem:
    kind: str
    name: str
    target_relative: str
    reason: str = "already_exists"


@dataclass
class PreflightResult:
    ok: bool
    policy: ConflictPolicy
    conflicts: List[ConflictItem] = field(default_factory=list)
    skipped: List[ManifestEntry] = field(default_factory=list)
    to_install: List[ManifestEntry] = field(default_factory=list)


@dataclass
class InstallResult:
    ok: bool
    installed: List[ManifestEntry] = field(default_factory=list)
    skipped: List[ManifestEntry] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
