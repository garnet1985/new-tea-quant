"""Facade class for export/import operations."""

from __future__ import annotations

from .core.namespaces import ArchiveNamespace, InstallNamespace
from .types import (
    ArtifactSpec,
    BundleManifest,
    CollectedFile,
    ConflictItem,
    ConflictPolicy,
    InstallResult,
    ManifestEntry,
    PreflightResult,
)


class ExportImport:
    """Facade class for userspace artifact bundle export/import operations."""

    archive: type = ArchiveNamespace
    install: type = InstallNamespace
    types = type("TypesNamespace", (), {
        "ArtifactSpec": ArtifactSpec,
        "BundleManifest": BundleManifest,
        "CollectedFile": CollectedFile,
        "ConflictItem": ConflictItem,
        "ConflictPolicy": ConflictPolicy,
        "InstallResult": InstallResult,
        "ManifestEntry": ManifestEntry,
        "PreflightResult": PreflightResult,
    })