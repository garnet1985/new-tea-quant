"""
sys_strategy_workbench_snapshot 表 Model。
"""

import threading
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.infra.db import DbBaseModel
from core.tables.ui_bff.strategy_workbench_snapshot.schema import schema as _schema


class SysStrategyWorkbenchSnapshotModel(DbBaseModel):
    """策略工作台快照版本表 Model（表名 sys_strategy_workbench_snapshot）。"""
    _table_ready = False
    _table_ready_lock = threading.Lock()

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    @staticmethod
    def _coerce_json_dict(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return dict(raw)
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except Exception:
                return {}
            return dict(parsed) if isinstance(parsed, dict) else {}
        return {}

    def _ensure_table_ready(self) -> None:
        if self.__class__._table_ready:
            return
        with self.__class__._table_ready_lock:
            if self.__class__._table_ready:
                return
            exists = False
            try:
                exists = self.db.is_table_exists(self.table_name)
            except Exception:
                exists = False
            if not exists:
                # 使用 schema_manager 按 schema 创建表 + 索引，避免首次查询报表不存在。
                self.db.schema_manager.create_table_with_indexes(self.schema, self.db.get_connection)
            self.__class__._table_ready = True

    def load_by_strategy_version(self, strategy_name: str, version: int) -> Optional[Dict[str, Any]]:
        self._ensure_table_ready()
        row = self.load_one("strategy_name = %s AND version = %s", (strategy_name, int(version)))
        return self._normalize_row(row) if row else None

    def list_by_strategy(self, strategy_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        self._ensure_table_ready()
        safe_limit = max(1, min(int(limit or 100), 500))
        # 按版本号降序：不能把 updated_at 当「最新」——update_result_summary 会改写旧行的 updated_at，
        # 否则会读到过时 settings_snapshot（枚举指纹不变 → 永远命中缓存）。
        rows = self.load(
            "strategy_name = %s",
            (strategy_name,),
            order_by="version DESC",
            limit=safe_limit,
        )
        return [self._normalize_row(row) for row in rows]

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(row or {})
        out["settings_snapshot"] = self._coerce_json_dict(out.get("settings_snapshot"))
        out["result_summary"] = self._coerce_json_dict(out.get("result_summary"))
        return out

    def get_next_version(self, strategy_name: str) -> int:
        self._ensure_table_ready()
        latest = self.load(
            "strategy_name = %s",
            (strategy_name,),
            order_by="version DESC",
            limit=1,
        )
        if not latest:
            return 1
        current = latest[0].get("version", 0) or 0
        return int(current) + 1

    def create_version(
        self,
        strategy_name: str,
        settings_snapshot: Dict[str, Any],
        result_summary: Optional[Dict[str, Any]] = None,
        enum_fingerprint_id: str = "",
        enum_scope_fingerprint_id: str = "",
    ) -> Dict[str, Any]:
        self._ensure_table_ready()
        version = self.get_next_version(strategy_name)
        now = datetime.now()
        payload = {
            "strategy_name": strategy_name,
            "version": version,
            "settings_snapshot": settings_snapshot or {},
            "result_summary": result_summary or {},
            "enum_fingerprint_id": str(enum_fingerprint_id or ""),
            "enum_scope_fingerprint_id": str(enum_scope_fingerprint_id or ""),
            "created_at": now,
            "updated_at": now,
        }
        self.upsert_one(payload, unique_keys=["strategy_name", "version"])
        return {"strategy_name": strategy_name, "version": version}

    def update_result_summary(
        self,
        strategy_name: str,
        version: int,
        result_summary: Dict[str, Any],
        enum_fingerprint_id: str = "",
        enum_scope_fingerprint_id: str = "",
    ) -> int:
        self._ensure_table_ready()
        current = self.load_by_strategy_version(strategy_name, version)
        if not current:
            return 0
        target_fp = (
            str(enum_fingerprint_id)
            if enum_fingerprint_id is not None and str(enum_fingerprint_id) != ""
            else str(current.get("enum_fingerprint_id") or "")
        )
        target_scope_fp = (
            str(enum_scope_fingerprint_id)
            if enum_scope_fingerprint_id is not None and str(enum_scope_fingerprint_id) != ""
            else str(current.get("enum_scope_fingerprint_id") or "")
        )
        return self.execute_raw_update(
            (
                "UPDATE sys_strategy_workbench_snapshot "
                "SET result_summary = %s, enum_fingerprint_id = %s, enum_scope_fingerprint_id = %s, updated_at = %s "
                "WHERE strategy_name = %s AND version = %s"
            ),
            (
                json.dumps(result_summary or {}, ensure_ascii=False),
                target_fp,
                target_scope_fp,
                datetime.now(),
                strategy_name,
                int(version),
            ),
        )

    def list_by_strategy_enum_fingerprint(
        self,
        strategy_name: str,
        *,
        enum_fingerprint_id: str = "",
        enum_scope_fingerprint_id: str = "",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        self._ensure_table_ready()
        safe_limit = max(1, min(int(limit or 100), 500))
        fp = str(enum_fingerprint_id or "").strip()
        scope_fp = str(enum_scope_fingerprint_id or "").strip()
        if fp and scope_fp:
            where = (
                "strategy_name = %s AND (enum_fingerprint_id = %s OR enum_scope_fingerprint_id = %s)"
            )
            params = (strategy_name, fp, scope_fp)
        elif fp:
            where = "strategy_name = %s AND enum_fingerprint_id = %s"
            params = (strategy_name, fp)
        elif scope_fp:
            where = "strategy_name = %s AND enum_scope_fingerprint_id = %s"
            params = (strategy_name, scope_fp)
        else:
            return []
        rows = self.load(where, params, order_by="version DESC", limit=safe_limit)
        return [self._normalize_row(row) for row in rows]

    def clear_enum_cache_for_version(self, strategy_name: str, version: int) -> int:
        """
        清理指定版本的枚举缓存字段（enum / enum_meta + fingerprint 列）。
        保留该版本其它结果（如 price / capital）与 settings_snapshot。
        """
        self._ensure_table_ready()
        current = self.load_by_strategy_version(strategy_name, version)
        if not current:
            return 0
        rs = self._coerce_json_dict(current.get("result_summary"))
        rs.pop("enum", None)
        rs.pop("enum_meta", None)
        return self.execute_raw_update(
            (
                "UPDATE sys_strategy_workbench_snapshot "
                "SET result_summary = %s, enum_fingerprint_id = %s, enum_scope_fingerprint_id = %s, updated_at = %s "
                "WHERE strategy_name = %s AND version = %s"
            ),
            (
                json.dumps(rs, ensure_ascii=False),
                "",
                "",
                datetime.now(),
                strategy_name,
                int(version),
            ),
        )

    def replace_enum_cache_by_fingerprint(
        self,
        *,
        strategy_name: str,
        enum_fingerprint_id: str,
        enum_scope_fingerprint_id: str,
    ) -> int:
        """
        Atomic-style replace semantics at model boundary:
        clear all rows matched by fingerprint/scope before inserting a new cache row.
        """
        rows = self.list_by_strategy_enum_fingerprint(
            strategy_name,
            enum_fingerprint_id=enum_fingerprint_id,
            enum_scope_fingerprint_id=enum_scope_fingerprint_id,
            limit=500,
        )
        cleared = 0
        for row in rows:
            version = int((row or {}).get("version") or 0)
            if version > 0 and self.clear_enum_cache_for_version(strategy_name, version):
                cleared += 1
        return cleared
