"""Multipart upload and conflict-policy helpers for strategy package routes."""

from __future__ import annotations

from typing import Optional, Tuple

from flask import request

from core.infra.export_import import ConflictPolicy
from core.ui.bff.shared.response import error


def read_uploaded_bytes(field: str = "file") -> Tuple[Optional[bytes], Optional[object]]:
    """Return ``(blob, error_response)``."""
    upload = request.files.get(field)
    if upload is None or not getattr(upload, "filename", ""):
        return None, error("缺少上传文件（multipart 字段 file）", 400)
    data = upload.read()
    if not data:
        return None, error("上传文件为空", 400)
    return data, None


def parse_conflict_policy(raw: Optional[str] = None) -> Tuple[Optional[ConflictPolicy], Optional[object]]:
    text = str(raw if raw is not None else "").strip().lower()
    if not text:
        text = str(request.args.get("policy") or request.form.get("policy") or "reject").strip().lower()
    mapping = {
        "reject": ConflictPolicy.REJECT,
        "skip_existing": ConflictPolicy.SKIP_EXISTING,
        "overwrite": ConflictPolicy.OVERWRITE,
    }
    policy = mapping.get(text)
    if policy is None:
        return None, error(
            f"无效 policy={text!r}；可选 reject | skip_existing | overwrite",
            400,
        )
    return policy, None
