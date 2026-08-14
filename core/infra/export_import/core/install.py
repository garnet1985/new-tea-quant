"""Install extracted bundle payload into userspace."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional, Union

from ..contracts import (
    BundleManifest,
    ConflictPolicy,
    InstallResult,
    ManifestEntry,
    PreflightResult,
)
from .conflict import ConflictChecker
from .manifest import BundleManifestIO


class BundleInstaller:
    """解压后落盘 / 从 archive 一键安装。"""

    @staticmethod
    def install_extracted(
        extracted_root: Path,
        userspace_root: Path,
        policy: ConflictPolicy,
        *,
        preflight: Optional[PreflightResult] = None,
    ) -> InstallResult:
        """
        Copy payload files from an extracted bundle into ``userspace_root``.

        Only entries allowed by ``preflight`` (or a fresh preflight) are applied.
        """
        root = Path(extracted_root)
        us = Path(userspace_root)
        us.mkdir(parents=True, exist_ok=True)

        manifest = BundleManifestIO.read(root / BundleManifestIO.FILENAME)
        plan = preflight or ConflictChecker.preflight(manifest, us, policy)
        if not plan.ok:
            return InstallResult(
                ok=False,
                errors=[
                    f"{c.kind} {c.name} already exists at {c.target_relative}"
                    for c in plan.conflicts
                ],
            )

        installed: List[ManifestEntry] = []
        errors: List[str] = []

        for entry in plan.to_install:
            try:
                BundleInstaller._install_entry(root, us, entry, policy)
                installed.append(entry)
            except Exception as exc:
                errors.append(f"failed to install {entry.kind} {entry.name}: {exc}")

        return InstallResult(
            ok=not errors,
            installed=installed,
            skipped=list(plan.skipped),
            errors=errors,
        )

    @staticmethod
    def install_archive(
        archive: Union[Path, bytes],
        userspace_root: Path,
        policy: ConflictPolicy,
    ) -> InstallResult:
        """Extract then install; uses a temporary directory for extraction."""
        from .archive import BundleArchive

        extracted, manifest = BundleArchive.extract(archive)
        preflight = ConflictChecker.preflight(
            manifest, Path(userspace_root), policy
        )
        if not preflight.ok:
            shutil.rmtree(extracted, ignore_errors=True)
            return InstallResult(
                ok=False,
                errors=[
                    f"{c.kind} {c.name} already exists at {c.target_relative}"
                    for c in preflight.conflicts
                ],
            )
        try:
            return BundleInstaller.install_extracted(
                extracted, userspace_root, policy, preflight=preflight
            )
        finally:
            shutil.rmtree(extracted, ignore_errors=True)

    @staticmethod
    def _install_entry(
        extracted_root: Path,
        userspace_root: Path,
        entry: ManifestEntry,
        policy: ConflictPolicy,
    ) -> None:
        prefix = entry.archive_prefix.strip("/")
        target_root = userspace_root / entry.target_relative

        if policy == ConflictPolicy.OVERWRITE and target_root.exists():
            if target_root.is_dir():
                shutil.rmtree(target_root)
            else:
                target_root.unlink()

        target_root.mkdir(parents=True, exist_ok=True)

        copied_any = False
        for path in extracted_root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(extracted_root).as_posix()
            if rel == BundleManifestIO.FILENAME:
                continue
            if not rel.startswith(prefix + "/") and rel != prefix:
                continue
            if rel == prefix:
                continue
            suffix = rel[len(prefix) + 1 :]
            dest = target_root / suffix
            dest.parent.mkdir(parents=True, exist_ok=True)
            BundleInstaller._atomic_copy(path, dest)
            copied_any = True

        if not copied_any:
            raise ValueError(f"no payload files found for archive_prefix={prefix}")

    @staticmethod
    def _atomic_copy(src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".ntq_import_tmp")
        shutil.copy2(src, tmp)
        os.replace(str(tmp), str(dest))
