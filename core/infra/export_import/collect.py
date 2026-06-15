"""Collect files from a source directory into bundle payload paths."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .runtime_excludes import should_skip_dir, should_skip_file
from .types import ArtifactSpec, CollectedFile


def collect_artifact_files(spec: ArtifactSpec) -> List[CollectedFile]:
    """
    Walk ``spec.source_dir`` and return files to place under ``archive_prefix/``.

    Raises ``FileNotFoundError`` when the source directory is missing.
    Raises ``ValueError`` when no files remain after filtering.
    """
    source = Path(spec.source_dir)
    if not source.is_dir():
        raise FileNotFoundError(f"artifact source directory not found: {source}")

    prefix = spec.normalized_archive_prefix()
    if not prefix:
        raise ValueError("artifact archive_prefix is required")

    collected: List[CollectedFile] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        if _is_under_skipped_dir(source, path):
            continue
        if should_skip_file(path):
            continue
        rel = path.relative_to(source).as_posix()
        archive_path = f"{prefix}/{rel}" if rel else prefix
        collected.append(CollectedFile(archive_path=archive_path, source_path=path))

    if not collected:
        raise ValueError(f"no exportable files under {source}")
    return collected


def _is_under_skipped_dir(root: Path, file_path: Path) -> bool:
    rel_parts = file_path.relative_to(root).parts
    current = root
    for part in rel_parts[:-1]:
        current = current / part
        if should_skip_dir(current.parent, part):
            return True
    return False
