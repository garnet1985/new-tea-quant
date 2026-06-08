"""Zip archive create/extract for userspace bundles."""

from __future__ import annotations

import io
import json
import logging
import shutil
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import List, Tuple, Union

from .collect import collect_artifact_files
from .manifest import MANIFEST_FILENAME, manifest_from_specs, read_manifest, write_manifest
from .types import ArtifactSpec, BundleManifest, CollectedFile

logger = logging.getLogger(__name__)

BytesOrPath = Union[bytes, Path]

_ZIP_DIR_MODE = stat.S_IFDIR | 0o755
_ZIP_FILE_MODE = stat.S_IFREG | 0o644


def create_bundle_archive(
    specs: List[ArtifactSpec],
    *,
    metadata: dict | None = None,
    output_path: Path | None = None,
) -> Tuple[BundleManifest, BytesOrPath]:
    """
    Build a zip bundle from artifact specs.

    Prefers the system ``zip`` tool on macOS/Linux (includes directory entries;
    ``-X`` strips Finder metadata). Falls back to stdlib zipfile with explicit
    directory records when ``zip`` is unavailable.
    """
    if not specs:
        raise ValueError("at least one ArtifactSpec is required")

    manifest = manifest_from_specs(specs, metadata=metadata)
    files: List[CollectedFile] = []
    for spec in specs:
        files.extend(collect_artifact_files(spec))

    with tempfile.TemporaryDirectory(prefix="ntq_bundle_stage_") as tmp:
        staging = Path(tmp) / "root"
        _populate_staging_tree(staging, manifest, files)

        if shutil.which("zip"):
            if output_path is None:
                out = Path(tmp) / "bundle.zip"
                _create_zip_via_system_zip(staging, out)
                return manifest, out.read_bytes()
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            _create_zip_via_system_zip(staging, out)
            return manifest, out

        logger.warning("system zip not found; falling back to stdlib zipfile")
        if output_path is None:
            buf = io.BytesIO()
            _create_zip_via_stdlib(buf, manifest, files)
            return manifest, buf.getvalue()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            _create_zip_via_stdlib(zf, manifest, files)
        return manifest, out


def extract_bundle_archive(
    source: Union[Path, bytes],
    *,
    dest_dir: Path | None = None,
) -> Tuple[Path, BundleManifest]:
    """
    Extract bundle to a directory (temporary if ``dest_dir`` omitted).

    Returns ``(extracted_root, manifest)``.
    """
    if dest_dir is None:
        dest_dir = Path(tempfile.mkdtemp(prefix="ntq_bundle_"))
    else:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(source, (bytes, bytearray)):
        zf = zipfile.ZipFile(io.BytesIO(source), mode="r")
        with zf:
            zf.extractall(dest_dir)
    else:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"bundle archive not found: {path}")
        with zipfile.ZipFile(path, mode="r") as zf:
            zf.extractall(dest_dir)

    manifest = read_manifest(dest_dir / MANIFEST_FILENAME)
    return dest_dir, manifest


def _populate_staging_tree(
    staging: Path,
    manifest: BundleManifest,
    files: List[CollectedFile],
) -> None:
    staging.mkdir(parents=True, exist_ok=True)
    write_manifest(manifest, staging)
    for item in files:
        dest = staging / item.archive_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item.source_path, dest)


def _create_zip_via_system_zip(staging: Path, output_path: Path) -> None:
    """``zip -r -X`` from staging root — matches macOS Archive Utility expectations."""
    output_path = Path(output_path)
    if output_path.exists():
        output_path.unlink()
    cmd = ["zip", "-r", "-X", str(output_path.resolve()), "."]
    proc = subprocess.run(
        cmd,
        cwd=str(staging),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"zip command failed: {err or proc.returncode}")


def _collect_directory_arcnames(files: List[CollectedFile]) -> List[str]:
    dirs = set()
    for item in files:
        parts = Path(item.archive_path).parts
        for i in range(1, len(parts)):
            dirs.add("/".join(parts[:i]) + "/")
    return sorted(dirs)


def _create_zip_via_stdlib(
    sink: Union[io.BytesIO, zipfile.ZipFile],
    manifest: BundleManifest,
    files: List[CollectedFile],
) -> None:
    owns_zip = isinstance(sink, io.BytesIO)
    if owns_zip:
        zf: zipfile.ZipFile = zipfile.ZipFile(sink, mode="w", compression=zipfile.ZIP_DEFLATED)
    else:
        zf = sink  # type: ignore[assignment]

    try:
        payload = json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n"
        zf.writestr(MANIFEST_FILENAME, payload.encode("utf-8"))

        for dir_name in _collect_directory_arcnames(files):
            info = zipfile.ZipInfo(dir_name)
            info.external_attr = _ZIP_DIR_MODE << 16
            zf.writestr(info, b"")

        for item in files:
            info = zipfile.ZipInfo(item.archive_path)
            info.external_attr = _ZIP_FILE_MODE << 16
            zf.writestr(info, item.source_path.read_bytes())
    finally:
        if owns_zip:
            zf.close()
