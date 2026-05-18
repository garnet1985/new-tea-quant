#!/usr/bin/env python3
"""发现 markets/*.json 并合并 core + userspace 配置。"""

from __future__ import annotations

from typing import Any, Dict, List


def list_profile_ids() -> List[str]:
    pass


def load_merged_profile(profile_id: str) -> Dict[str, Any]:
    pass


__all__ = ["list_profile_ids", "load_merged_profile"]
