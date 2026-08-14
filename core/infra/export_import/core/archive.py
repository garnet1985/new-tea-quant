"""Zip archive create/extract for userspace bundles (stdlib zipfile only)."""

from __future__ import annotations

import io
import logging
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import List, Tuple, Union

from ..contracts import ArtifactSpec, BundleManifest, CollectedFile
from .collect import ArtifactCollector
from .manifest import BundleManifestIO

logger = logging.getLogger(__name__)

BytesOrPath = Union[bytes, Path]

_ZIP_DIR_MODE = stat.S_IFDIR | 0o755
_ZIP_FILE_MODE = stat.S_IFREG | 0o644


class BundleArchive:
    """制品 zip 打包 / 解压（唯一实现：stdlib ``zipfile``）。"""

    @staticmethod
    def create(
        specs: List[ArtifactSpec],
        *,
        metadata: dict | None = None,
        output_path: Path | None = None,
    ) -> Tuple[BundleManifest, BytesOrPath]:
        """按 ArtifactSpec 收集文件并打 zip；``output_path`` 缺省则返回 bytes。"""
        if not specs:
            raise ValueError("at least one ArtifactSpec is required")

        manifest = BundleManifestIO.from_specs(specs, metadata=metadata)
        files: List[CollectedFile] = []
        for spec in specs:
            files.extend(ArtifactCollector.collect(spec))

        with tempfile.TemporaryDirectory(prefix="ntq_bundle_stage_") as tmp:
            staging = Path(tmp) / "root"
            BundleArchive._populate_staging_tree(staging, manifest, files)

            if output_path is None:
                buf = io.BytesIO()
                BundleArchive._zip_staging_tree(staging, buf)
                return manifest, buf.getvalue()

            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(
                out, mode="w", compression=zipfile.ZIP_DEFLATED
            ) as zf:
                BundleArchive._zip_staging_tree(staging, zf)
            return manifest, out

    @staticmethod
    def extract(
        source: Union[Path, bytes],
        *,
        dest_dir: Path | None = None,
    ) -> Tuple[Path, BundleManifest]:
        """解压到目录（缺省临时目录）；返回 ``(extracted_root, manifest)``。"""
        if dest_dir is None:
            dest_dir = Path(tempfile.mkdtemp(prefix="ntq_bundle_"))
        else:
            dest_dir = Path(dest_dir)
            dest_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(source, (bytes, bytearray)):
            with zipfile.ZipFile(io.BytesIO(source), mode="r") as zf:
                zf.extractall(dest_dir)
        else:
            path = Path(source)
            if not path.is_file():
                raise FileNotFoundError(f"bundle archive not found: {path}")
            with zipfile.ZipFile(path, mode="r") as zf:
                zf.extractall(dest_dir)

        manifest = BundleManifestIO.read(dest_dir / BundleManifestIO.FILENAME)
        return dest_dir, manifest

    @staticmethod
    def _populate_staging_tree(
        staging: Path,
        manifest: BundleManifest,
        files: List[CollectedFile],
    ) -> None:
        staging.mkdir(parents=True, exist_ok=True)
        BundleManifestIO.write(manifest, staging)
        for item in files:
            dest = staging / item.archive_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item.source_path, dest)

    @staticmethod
    def _zip_staging_tree(
        staging: Path,
        sink: Union[io.BytesIO, zipfile.ZipFile],
    ) -> None:
        owns_zip = isinstance(sink, io.BytesIO)
        if owns_zip:
            zf: zipfile.ZipFile = zipfile.ZipFile(
                sink, mode="w", compression=zipfile.ZIP_DEFLATED
            )
        else:
            zf = sink  # type: ignore[assignment]

        try:
            # Explicit directory entries for stable unzip across tools.
            dirs: set[str] = set()
            files: List[Path] = []
            for path in sorted(staging.rglob("*")):
                rel = path.relative_to(staging).as_posix()
                if path.is_dir():
                    dirs.add(rel.rstrip("/") + "/")
                elif path.is_file():
                    files.append(path)
                    parts = Path(rel).parts
                    for i in range(1, len(parts)):
                        dirs.add("/".join(parts[:i]) + "/")

            for dir_name in sorted(dirs):
                info = zipfile.ZipInfo(dir_name)
                info.external_attr = _ZIP_DIR_MODE << 16
                zf.writestr(info, b"")

            for path in files:
                rel = path.relative_to(staging).as_posix()
                info = zipfile.ZipInfo(rel)
                info.external_attr = _ZIP_FILE_MODE << 16
                zf.writestr(info, path.read_bytes())
        finally:
            if owns_zip:
                zf.close()
