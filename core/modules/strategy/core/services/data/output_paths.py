"""enumerate 输出路径解析。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OutputPathManager:
    """确定 output_dir 与 version_id。"""

    @staticmethod
    def resolve_output_dir(
        strategy_name: str,
        version_id: int,
        *,
        userspace_root: Optional[Path] = None,
    ) -> Path:
        root = userspace_root or Path("userspace")
        output_dir = root / strategy_name / "versions" / f"v{version_id}"
        logger.info("Resolved output_dir: %s", output_dir)
        return output_dir

    @staticmethod
    def resolve_version_id(
        strategy_name: str,
        *,
        fingerprint_hash: Optional[str] = None,
        userspace_root: Optional[Path] = None,
    ) -> int:
        _ = strategy_name, fingerprint_hash, userspace_root
        version_id = 1
        logger.info("Resolved version_id: %d (simplified)", version_id)
        return version_id

    @staticmethod
    def resolve_all_paths(
        strategy_name: str,
        *,
        fingerprint_hash: Optional[str] = None,
        userspace_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        version_id = OutputPathManager.resolve_version_id(
            strategy_name,
            fingerprint_hash=fingerprint_hash,
            userspace_root=userspace_root,
        )
        output_dir = OutputPathManager.resolve_output_dir(
            strategy_name,
            version_id,
            userspace_root=userspace_root,
        )
        return {
            "output_dir": output_dir,
            "version_id": version_id,
            "version_dir_name": f"v{version_id}",
        }


__all__ = ["OutputPathManager"]
