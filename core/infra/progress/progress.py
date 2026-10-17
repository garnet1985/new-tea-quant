"""进度门面。调用方从 core.infra.progress 导入。"""
from __future__ import annotations

from core.infra.progress.contracts import ProgressSnapshot
from core.infra.progress.core.store import Progress as _Store


class _Types:
    Snapshot = ProgressSnapshot


_Store.types = _Types
Progress = _Store

__all__ = ["Progress"]
