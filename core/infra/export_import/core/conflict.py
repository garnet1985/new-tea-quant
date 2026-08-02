"""Install-time conflict detection."""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..contracts import BundleManifest, ConflictItem, ConflictPolicy, ManifestEntry, PreflightResult


def preflight_install(
    manifest: BundleManifest,
    userspace_root: Path,
    policy: ConflictPolicy,
) -> PreflightResult:
    """
    Decide which manifest entries can be installed under ``userspace_root``.

    - ``reject``: any existing target root blocks the whole operation.
    - ``skip_existing``: existing roots are skipped; others proceed.
    - ``overwrite``: all entries proceed (existing trees may be replaced).
    """
    root = Path(userspace_root)
    conflicts: List[ConflictItem] = []
    skipped: List[ManifestEntry] = []
    to_install: List[ManifestEntry] = []

    for entry in manifest.entries:
        target = root / entry.target_relative
        exists = target.exists()
        if not exists:
            to_install.append(entry)
            continue

        if policy == ConflictPolicy.OVERWRITE:
            to_install.append(entry)
            continue

        if policy == ConflictPolicy.SKIP_EXISTING:
            skipped.append(entry)
            continue

        conflicts.append(
            ConflictItem(
                kind=entry.kind,
                name=entry.name,
                target_relative=entry.target_relative,
            )
        )

    ok = not conflicts
    return PreflightResult(
        ok=ok,
        policy=policy,
        conflicts=conflicts,
        skipped=skipped,
        to_install=to_install,
    )