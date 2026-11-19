"""Application facade used by CLI handlers."""

from __future__ import annotations

from typing import Optional

from core.infra.cmd_layout import i

from core.modules.data_manager import DataManager
from core.modules.data_source import DataSourceManager


class CliApp:
    """Lazy-initialized services for CLI commands."""

    def __init__(self, *, is_verbose: bool = False) -> None:
        self.is_verbose = is_verbose
        self.data_manager = DataManager(is_verbose=is_verbose)
        self.db = self.data_manager.db
        self.data_source = DataSourceManager()
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
        from core.modules.tag import Tag

        overrides: dict = {}
        if entity_limit is not None:
            overrides["entity_limit"] = max(1, int(entity_limit))
        Tag(
            is_verbose=self.is_verbose,
            dispatch_overrides=overrides or None,
        ).execute(scenario_name=scenario_name, dry_run=dry_run)

    def export_adj_factor_csv(
        self,
        base_date: str | None = None,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        file_path: str | None = None,
    ) -> None:
        out = self.data_manager.export_adj_factor_events_csv(
            base_date=base_date,
            start_date=start_date,
            end_date=end_date,
            file_path=file_path,
        )
        if not out.get("ok"):
            raise RuntimeError(str(out.get("error") or "导出失败"))
        start = out.get("start") or "?"
        end = out.get("end") or "?"
        path = out.get("path") or ""
        print(
            f"{i('upload')} 导出复权因子事件 CSV: {start} .. {end} -> {path}",
            flush=True,
        )
        print(
            f"{i('success')} 导出完成: {out.get('rows') or 0} 条 -> {path}",
            flush=True,
        )
