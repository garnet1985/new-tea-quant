"""Application facade used by CLI handlers."""

from __future__ import annotations

import logging
import os
from typing import Optional

from core.modules.data_manager import DataManager
from core.modules.data_source import DataSourceManager

logger = logging.getLogger(__name__)


class CliApp:
    """Lazy-initialized services for CLI commands."""

    def __init__(self, *, is_verbose: bool = False) -> None:
        self.is_verbose = is_verbose
        self.data_manager = DataManager(is_verbose=is_verbose)
        self.db = self.data_manager.db
        self.data_source = DataSourceManager(is_verbose=is_verbose)
        self._tag = None

    async def renew_data(
        self,
        table_name: Optional[str] = None,
        *,
        force: bool = False,
    ) -> None:
        self.data_source.renew(table_name=table_name, force=force)

    def _ensure_tag(self):
        if self._tag is None:
            from core.modules.tag import Tag

            self._tag = Tag(is_verbose=self.is_verbose)
        return self._tag

    def list_tags(self, *, enabled_only: bool = False) -> list[str]:
        """列出已发现的 tag 路径 id（相对 tags 根）。"""
        return self._ensure_tag().list_ids(enabled_only=enabled_only)

    def tag(
        self,
        scenario_name: str | None = None,
        *,
        dry_run: bool = False,
        entity_limit: int | None = None,
    ) -> None:
        tag = self._ensure_tag()
        overrides: dict = {}
        if entity_limit is not None:
            overrides["entity_limit"] = max(1, int(entity_limit))
        tag._dispatch_overrides = overrides
        tag.execute(scenario_name=scenario_name, dry_run=dry_run)

    def export_adj_factor_csv(
        self,
        base_date: str | None = None,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        file_path: str | None = None,
    ) -> None:
        adj_model = self.data_manager.stock.kline._adj_factor_event
        resolved_start = (
            str(start_date).replace("-", "")[:8]
            if start_date
            else adj_model.get_min_event_date()
        )
        end = end_date or adj_model.get_max_event_date()
        if file_path:
            out = file_path
        elif base_date and not end_date and start_date is None:
            file_name = adj_model.get_current_quarter_csv_name(base_date=base_date)
            out = os.path.join(adj_model.csv_dir, file_name)
        else:
            out = os.path.join(
                adj_model.csv_dir,
                f"adj_factor_events_{resolved_start or 'earliest'}_{end or 'latest'}.csv",
            )
        logger.info("📤 导出复权因子事件 CSV: %s .. %s -> %s", resolved_start, end or "?", out)
        exported = adj_model.export_to_csv(
            file_path=out, start_date=start_date, end_date=end_date
        )
        logger.info("✅ 导出完成: %s 条 -> %s", exported, out)
