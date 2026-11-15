"""扫描后处理是否执行的工作区偏好。

路径：``userspace/system/prefs/post_process_run.json``
键：``enable_post_process`` — **默认开启**；关闭需显式写 ``false``；开启则去掉声明。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_FILENAME = "post_process_run.json"
_KEY = "enable_post_process"


class RunPrefs:
    @staticmethod
    def is_enabled() -> bool:
        raw = RunPrefs._read() or {}
        if _KEY not in raw:
            return True
        return bool(raw.get(_KEY))

    @staticmethod
    def set_enabled(enabled: bool) -> bool:
        try:
            path = RunPrefs._path()
            if path is None:
                return False
            data = dict(RunPrefs._read() or {})
            if enabled:
                data.pop(_KEY, None)
            else:
                data[_KEY] = False
            if not data:
                if path.is_file():
                    path.unlink()
                return True
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return True
        except Exception as exc:
            logger.warning("post_process run prefs write failed: %s", exc)
            return False

    @staticmethod
    def _path() -> Optional[Path]:
        try:
            from core.infra.project_context import ProjectContext

            return ProjectContext.path.get_user_prefs_root() / _FILENAME
        except Exception as exc:
            logger.debug("post_process run prefs path unavailable: %s", exc)
            return None

    @staticmethod
    def _read() -> Optional[Dict[str, Any]]:
        path = RunPrefs._path()
        if path is None or not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else None
        except Exception as exc:
            logger.debug("post_process run prefs read failed: %s", exc)
            return None


__all__ = ["RunPrefs"]
