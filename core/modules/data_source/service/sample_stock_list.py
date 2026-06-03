"""
从 stock_list 截取样本，用于 JobPipeline / renew 试跑（非全量）。

环境变量（任一生效即可，未设置则不截取）：
  NTQ_DS_SAMPLE_N 或 NTQ_DS_SAMPLE_SIZE — 最多保留几只（>0）
  NTQ_DS_SAMPLE_OFFSET — 起始下标，默认 0（按 DB/依赖列表顺序截取一段）

试跑默认只数见 ``DEFAULT_SAMPLE_N``（需覆盖 JobPipeline 并行 + Provider 限流，不宜过小）。
"""
from __future__ import annotations

# 样本 renew 推荐默认：≈ JobPipeline auto worker 数 × 10，够打满 in-flight 并触发限流
DEFAULT_SAMPLE_N = 80

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_LOGGED = False


def sample_limit() -> Optional[int]:
    """返回样本上限；None 表示不启用。"""
    for key in ("NTQ_DS_SAMPLE_N", "NTQ_DS_SAMPLE_SIZE"):
        raw = os.environ.get(key, "").strip()
        if not raw:
            continue
        try:
            n = int(raw)
        except ValueError:
            logger.warning("忽略无效的 %s=%r（需为正整数）", key, raw)
            continue
        if n > 0:
            return n
    return None


def sample_offset() -> int:
    raw = os.environ.get("NTQ_DS_SAMPLE_OFFSET", "0").strip() or "0"
    try:
        return max(0, int(raw))
    except ValueError:
        logger.warning("忽略无效的 NTQ_DS_SAMPLE_OFFSET=%r，使用 0", raw)
        return 0


def is_sample_active() -> bool:
    return sample_limit() is not None


def slice_stock_list(rows: List[Any]) -> List[Any]:
    """按 offset + limit 截取 stock_list；未启用时原样返回。"""
    global _LOGGED
    limit = sample_limit()
    if limit is None or not rows:
        return rows

    offset = sample_offset()
    end = min(offset + limit, len(rows))
    if offset >= len(rows):
        sliced: List[Any] = []
    else:
        sliced = list(rows[offset:end])

    if not _LOGGED:
        _LOGGED = True
        logger.info(
            "📎 stock_list 样本模式: 全量 %s 只 → 截取 [%s:%s] 共 %s 只 "
            "(NTQ_DS_SAMPLE_N=%s, OFFSET=%s)",
            len(rows),
            offset,
            end,
            len(sliced),
            limit,
            offset,
        )
    return sliced


def slice_stock_list_in_dependencies(deps: Dict[str, Any]) -> Dict[str, Any]:
    """若 dependencies 含 stock_list，替换为截取后的列表（浅拷贝 dict）。"""
    if "stock_list" not in deps:
        return deps
    raw = deps.get("stock_list")
    if not isinstance(raw, list):
        return deps
    sliced = slice_stock_list(raw)
    if sliced is raw:
        return deps
    out = dict(deps)
    out["stock_list"] = sliced
    return out
