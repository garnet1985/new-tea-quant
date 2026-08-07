#!/usr/bin/env python3
"""归档读写（内部实现；公开入口 ``Utils.io``）。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal, Optional
import io
import tarfile
import time
import zipfile


class FileIo:
    """zip / tar.gz / 单文件 CSV 读写。"""

    @staticmethod
    def write_archive(
        output_dir: str | Path,
        archive_name: str,
        files: Dict[str, bytes],
        *,
        format: Literal["tar.gz", "zip"] = "tar.gz",
    ) -> Path:
        """在 ``output_dir`` 下生成归档；``archive_name`` 不含扩展名。"""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        ext = "tar.gz" if format == "tar.gz" else "zip"
        archive_path = out_dir / f"{archive_name}.{ext}"

        if format == "tar.gz":
            with tarfile.open(archive_path, "w:gz", compresslevel=9) as tf:
                now_ts = time.time()
                for name, content in files.items():
                    info = tarfile.TarInfo(name=name)
                    info.size = len(content)
                    info.mtime = now_ts
                    tf.addfile(info, io.BytesIO(content))
        else:
            with zipfile.ZipFile(
                archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9
            ) as zf:
                for name, content in files.items():
                    zf.writestr(name, content)

        return archive_path

    @staticmethod
    def read_archive_files(
        archive_path: str | Path,
        *,
        filter_ext: Optional[str] = None,
    ) -> Dict[str, bytes]:
        """从归档或单一 CSV 读取 ``{文件名: bytes}``。"""
        path = Path(archive_path)
        result: Dict[str, bytes] = {}

        if path.suffix.lower() == ".csv":
            result[path.name] = path.read_bytes()
            return result

        suffix = path.suffix.lower()
        if suffix == ".zip":
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    name = info.filename
                    if info.is_dir():
                        continue
                    if filter_ext and not name.lower().endswith(filter_ext.lower()):
                        continue
                    with zf.open(info) as f:
                        result[name] = f.read()
            return result

        with tarfile.open(path, "r:*") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                name = member.name
                if filter_ext and not name.lower().endswith(filter_ext.lower()):
                    continue
                extracted = tf.extractfile(member)
                if extracted is None:
                    continue
                result[name] = extracted.read()

        return result


__all__ = ["FileIo"]
