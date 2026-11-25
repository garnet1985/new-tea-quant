"""导入三年窗演示/会员包后，把 userspace data.json 对齐到数据包日期窗。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from core.infra.setup.core.steps.import_data.export.config import (
    DEFAULT_END_DATE,
    DEFAULT_START_DATE,
)

logger = logging.getLogger(__name__)

# 与 core/default_config/data.json 一致：未写 userspace 覆盖时的默认起点。
_CORE_DEFAULT_START = "20080101"
_PACK_KINDS = frozenset({"demo", "member"})


def align_data_json_to_pack_window(
    *,
    pack_kind: str,
    userspace_data_json: Optional[Path] = None,
) -> Dict[str, Any]:
    """导入 demo/member 成功后调用：创建或补写 userspace ``data.json`` 日期窗。

    - 仅处理 ``demo`` / ``member``（与导出默认窗 20230101–20251231 一致）。
    - ``default_start_date``：缺省或仍为 core 默认 ``20080101`` 时改为包起点。
    - ``assumed_latest_completed_trading_date``：缺省 / null / 空时改为包终点。
    - 用户已手改过的值不覆盖。
    """
    kind = str(pack_kind or "").strip().lower()
    if kind not in _PACK_KINDS:
        return {"changed": False, "skipped": True, "reason": f"pack_kind={kind!r}"}

    path = userspace_data_json
    if path is None:
        from core.infra.project_context import ProjectContext

        path = ProjectContext.path.get_user_config_root() / "data.json"

    existing: Dict[str, Any] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = dict(loaded)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("读取 %s 失败，将按空配置重写日期窗: %s", path, exc)

    changed: Dict[str, str] = {}
    start_raw = existing.get("default_start_date", None)
    start = str(start_raw).strip().replace("-", "")[:8] if start_raw is not None else ""
    if start_raw is None or start in ("", _CORE_DEFAULT_START):
        if start != DEFAULT_START_DATE:
            existing["default_start_date"] = DEFAULT_START_DATE
            changed["default_start_date"] = DEFAULT_START_DATE

    assumed_raw = existing.get("assumed_latest_completed_trading_date", None)
    assumed = (
        str(assumed_raw).strip().replace("-", "")[:8]
        if assumed_raw is not None
        else ""
    )
    if assumed_raw is None or assumed in ("", "null", "None"):
        if assumed != DEFAULT_END_DATE:
            existing["assumed_latest_completed_trading_date"] = DEFAULT_END_DATE
            changed["assumed_latest_completed_trading_date"] = DEFAULT_END_DATE

    if not changed:
        return {
            "changed": False,
            "skipped": False,
            "path": str(path),
            "pack_kind": kind,
        }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "已对齐 data.json 到数据包日期窗 kind=%s path=%s changes=%s",
        kind,
        path,
        changed,
    )
    return {
        "changed": True,
        "skipped": False,
        "path": str(path),
        "pack_kind": kind,
        "updates": changed,
    }
