"""
Export / Import infrastructure for userspace artifact bundles.

Business-specific bundle assembly (e.g. strategy packages) belongs in domain
modules; this package provides zip, manifest, collection, conflict checks,
and installation primitives.
"""

from .archive import create_bundle_archive, extract_bundle_archive
from .collect import collect_artifact_files
from .conflict import preflight_install
from .install import install_bundle, install_bundle_archive
from .manifest import (
    MANIFEST_FILENAME,
    SUPPORTED_FORMAT_VERSION,
    manifest_from_specs,
    read_manifest,
    validate_manifest,
    write_manifest,
)
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

__all__ = [
    "ArtifactSpec",
    "BundleManifest",
    "CollectedFile",
    "ConflictItem",
    "ConflictPolicy",
    "InstallResult",
    "MANIFEST_FILENAME",
    "ManifestEntry",
    "PreflightResult",
    "SUPPORTED_FORMAT_VERSION",
    "collect_artifact_files",
    "create_bundle_archive",
    "extract_bundle_archive",
    "install_bundle",
    "install_bundle_archive",
    "manifest_from_specs",
    "preflight_install",
    "read_manifest",
    "validate_manifest",
    "write_manifest",
]
