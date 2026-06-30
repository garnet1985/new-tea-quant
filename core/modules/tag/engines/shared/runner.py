"""Tag 执行收尾工具（DuckDB spill 目录、CHECKPOINT）。"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from core.infra.project_context import ProjectContext
from core.infra.db.engines.duckdb.wal_policy import should_checkpoint_after_tag_run
from core.modules.tag.services.discovery.path_rules import filesystem_safe_tag_key

logger = logging.getLogger(__name__)


def _make_tag_spill_dir(scenario_name: str) -> Path:
    """DuckDB stage spill 临时目录（``tag_key`` 含 ``/`` 时须 sanitize prefix）。"""
    parent = ProjectContext.path.get_userspace_tmp_directory() / "tag_spill"
    parent.mkdir(parents=True, exist_ok=True)
    prefix = f"ntq_tag_{filesystem_safe_tag_key(scenario_name)}_"
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(parent)))


def maybe_checkpoint_duckdb_after_tag_run(data_mgr: Any) -> None:
    db = getattr(data_mgr, "db", None) if data_mgr else None
    if db is None or str(db.config.get("database_type") or "").lower() != "duckdb":
        return
    if not should_checkpoint_after_tag_run(db.config):
        return
    try:
        results = db.checkpoint_duckdb()
        if not results:
            return
        failed = [d for d, ok in results.items() if not ok]
        ok_domains = sorted(d for d, ok in results.items() if ok)
        if failed:
            logger.warning(
                "DuckDB WAL 合并未完成: 失败 domain=%s；成功=%s。"
                "（写队列忙时可重试 devcli.py dbc --recover）",
                failed,
                ok_domains,
            )
        else:
            logger.info("DuckDB WAL 已合并（domains=%s）", ok_domains)
    except Exception as exc:
        logger.warning(
            "Tag 完成后 CHECKPOINT 异常（若下次启动报 WAL: python devcli.py dbc --recover）: %s",
            exc,
        )


__all__ = ["_make_tag_spill_dir", "maybe_checkpoint_duckdb_after_tag_run"]
