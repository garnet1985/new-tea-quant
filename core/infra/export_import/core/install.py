"""Install extracted bundle payload into userspace."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional, Union

from .conflict import preflight_install
from .manifest import read_manifest
from ..types import (
    BundleManifest,
    ConflictPolicy,
    InstallResult,
    ManifestEntry,
    PreflightResult,
)


def install_bundle(
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

    manifest = read_manifest(root / "manifest.json")
    plan = preflight or preflight_install(manifest, us, policy)
    if not plan.ok:
        return InstallResult(
            ok=False,
            errors=[f"{c.kind} {c.name} already exists at {c.target_relative}" for c in plan.conflicts],
        )

    installed: List[ManifestEntry] = []
    errors: List[str] = []

    for entry in plan.to_install:
        try:
            _install_entry(root, us, entry, policy)
            installed.append(entry)
        except Exception as exc:
            errors.append(f"failed to install {entry.kind} {entry.name}: {exc}")

    return InstallResult(
        ok=not errors,
        installed=installed,
        skipped=list(plan.skipped),
        errors=errors,
    )


def install_bundle_archive(
    archive: Union[Path, bytes],
    userspace_root: Path,
    policy: ConflictPolicy,
) -> InstallResult:
    """Extract then install; uses a temporary directory for extraction."""
    from .archive import extract_bundle_archive

    extracted, manifest = extract_bundle_archive(archive)
    preflight = preflight_install(manifest, Path(userspace_root), policy)
    if not preflight.ok:
        return InstallResult(
            ok=False,
            errors=[f"{c.kind} {c.name} already exists at {c.target_relative}" for c in preflight.conflicts],
        )
    try:
        return install_bundle(extracted, userspace_root, policy, preflight=preflight)
    finally:
        shutil.rmtree(extracted, ignore_errors=True)


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
        if rel == "manifest.json":
            continue
        if not rel.startswith(prefix + "/") and rel != prefix:
            continue
        if rel == prefix:
            continue
        suffix = rel[len(prefix) + 1 :]
        dest = target_root / suffix
        dest.parent.mkdir(parents=True, exist_ok=True)
        _atomic_copy(path, dest)
        copied_any = True

    if not copied_any:
        raise ValueError(f"no payload files found for archive_prefix={prefix}")


def _atomic_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".ntq_import_tmp")
    shutil.copy2(src, tmp)
    os.replace(str(tmp), str(dest))