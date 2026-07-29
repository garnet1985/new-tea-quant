#!/usr/bin/env python3
"""
通用文件/归档 IO 工具：

- 将内存中的文件内容写入 zip / tar.gz 归档
- 从 zip / tar.gz / csv 文件中读取原始 bytes
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal, Optional
import tarfile
import zipfile
import io
import time


def write_archive(
    output_dir: str | Path,
    archive_name: str,
    files: Dict[str, bytes],
    *,
    format: Literal["tar.gz", "zip"] = "tar.gz",
) -> Path:
    """
    在 output_dir 下生成一个归档文件：

    - archive_name: 不带扩展名的归档名，例如 "sys_stock_indicators"
    - files: {内部文件名: bytes 内容}
    - format: "tar.gz" 或 "zip"
    """
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


def read_archive_files(
    archive_path: str | Path,
    *,
    filter_ext: Optional[str] = None,
) -> Dict[str, bytes]:
    """
    从归档或单一 CSV 文件读取内容，返回 {文件名: bytes}。

    - 如果是 .csv：直接读取文件为 bytes，key 为文件名
    - 如果是 .zip/.tar.gz：遍历其中的成员文件，按 filter_ext 过滤
    """
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
                if not info.is_dir():
                    if filter_ext and not name.lower().endswith(filter_ext.lower()):
                        continue
                    with zf.open(info) as f:
                        result[name] = f.read()
        return result

    # 其余视为 tar 归档（tar.gz / .tar 等）
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

