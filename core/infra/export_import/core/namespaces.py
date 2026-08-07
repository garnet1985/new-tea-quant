"""Namespace classes for ExportImport facade."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Union

from ..contracts import (
    ArtifactSpec,
    BundleManifest,
    ConflictPolicy,
    InstallResult,
    PreflightResult,
)
from .archive import BundleArchive
from .conflict import ConflictChecker
from .install import BundleInstaller
from .manifest import BundleManifestIO


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
        return BundleArchive.create(
            specs, metadata=metadata, output_path=output_path
        )

    @staticmethod
    def extract(
        source: Union[Path, bytes],
        *,
        dest_dir: Path | None = None,
    ) -> Tuple[Path, BundleManifest]:
        """Extract bundle archive to a directory."""
        return BundleArchive.extract(source, dest_dir=dest_dir)


class InstallNamespace:
    """Namespace for installation operations."""

    @staticmethod
    def install(
        archive: Union[Path, bytes],
        userspace_root: Path,
        policy: ConflictPolicy,
    ) -> InstallResult:
        """Install bundle archive into userspace."""
        return BundleInstaller.install_archive(archive, userspace_root, policy)

    @staticmethod
    def preflight(
        extracted_root: Union[Path, BundleManifest],
        userspace_root: Path,
        policy: ConflictPolicy,
    ) -> PreflightResult:
        """Preflight installation (extracted root or BundleManifest)."""
        if isinstance(extracted_root, BundleManifest):
            manifest = extracted_root
        else:
            manifest = BundleManifestIO.read(
                Path(extracted_root) / BundleManifestIO.FILENAME
            )
        return ConflictChecker.preflight(manifest, userspace_root, policy)
