"""Namespace classes for ExportImport facade."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Union

from ..contracts import ArtifactSpec, BundleManifest, ConflictPolicy, InstallResult, PreflightResult
from .archive import create_bundle_archive, extract_bundle_archive
from .install import install_bundle, install_bundle_archive


class ArchiveNamespace:
    """Namespace for archive operations."""

    @staticmethod
    def create(
        specs: List[ArtifactSpec],
        *,
        metadata: dict | None = None,
        output_path: Path | None = None,
    ) -> Tuple[BundleManifest, Union[bytes, Path]]:
        """Create a bundle archive from artifact specs."""
        return create_bundle_archive(specs, metadata=metadata, output_path=output_path)

    @staticmethod
    def extract(
        source: Union[Path, bytes],
        *,
        dest_dir: Path | None = None,
    ) -> Tuple[Path, BundleManifest]:
        """Extract bundle archive to a directory."""
        return extract_bundle_archive(source, dest_dir=dest_dir)


class InstallNamespace:
    """Namespace for installation operations."""

    @staticmethod
    def install(
        archive: Union[Path, bytes],
        userspace_root: Path,
        policy: ConflictPolicy,
    ) -> InstallResult:
        """Install bundle archive into userspace."""
        return install_bundle_archive(archive, userspace_root, policy)

    @staticmethod
    def preflight(
        extracted_root: Union[Path, BundleManifest],
        userspace_root: Path,
        policy: ConflictPolicy,
    ) -> PreflightResult:
        """Preflight installation to detect conflicts."""
        from .conflict import preflight_install
        from .manifest import read_manifest

        if isinstance(extracted_root, BundleManifest):
            manifest = extracted_root
        else:
            manifest = read_manifest(extracted_root / "manifest.json")

        return preflight_install(manifest, userspace_root, policy)