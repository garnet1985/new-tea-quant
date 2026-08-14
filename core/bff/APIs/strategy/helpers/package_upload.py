"""Multipart upload helper for strategy package routes."""

from __future__ import annotations

from typing import Optional, Tuple

from flask import request

from core.bff.shared.response import error


def read_uploaded_bytes(field: str = "file") -> Tuple[Optional[bytes], Optional[object]]:
    """Return ``(blob, error_response)``."""
    upload = request.files.get(field)
    if upload is None or not getattr(upload, "filename", ""):
        return None, error("缺少上传文件（multipart 字段 file）", 400)
    data = upload.read()
    if not data:
        return None, error("上传文件为空", 400)
    return data, None
