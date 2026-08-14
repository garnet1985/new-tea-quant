"""
sys_strategy_workbench_snapshot 表 Model。

命名约定：表中列 ``version`` 为工作台快照整型版本号（一条快照一行）；
``version_id`` / ``v{n}`` 仅作展示用字符串。与磁盘模拟产物 ``output_version`` 无关。

JSON 聚合列在 schema 中为 ``reports``；读出行上同时提供 ``result_report`` 键（与 ``reports`` 同一 dict），便于调用方沿用原有命名。
"""

import json
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.infra.db.contracts import DbBaseModel
from core.tables.ui_bff.strategy_workbench_snapshot.schema import schema as _schema

COL_STRATEGY_KEY = "strategy_key"
COL_SETTINGS_FP = "settings_fingerprint_id"
COL_ENV_FP = "env_fingerprint_id"
COL_REPORTS = "reports"
COL_SETTINGS_DIFF = "settings_diff"


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
                self.db.schema_manager.create_table_with_indexes(
                    self.schema, self.db.get_connection
                )
            self.__class__._table_ready = True

    @staticmethod
    def _identity_aliases(strategy_name: str) -> List[str]:
        """Canonical ``meta.key`` + legacy path aliases for dual-read."""
        needle = str(strategy_name or "").strip()
        if not needle:
            return []
        aliases: List[str] = []

        def _add(value: Any) -> None:
            text = str(value or "").strip()
            if text and text not in aliases:
                aliases.append(text)

        _add(needle)
        try:
            from core.modules.strategy import Strategy

            info = Strategy.find(needle, enabled_only=False)
            if info:
                _add(info.get("key"))
                _add(info.get("unique_relative_path"))
                _add(info.get("relative_path"))
        except Exception:
            pass
        return aliases

    @staticmethod
    def _canonical_strategy_key(strategy_name: str) -> str:
        """Persist as ``meta.key`` when discoverable; else keep the given needle."""
        needle = str(strategy_name or "").strip()
        if not needle:
            return ""
        try:
            from core.modules.strategy import Strategy

            info = Strategy.find(needle, enabled_only=False)
            if info:
                key = str(info.get("key") or "").strip()
                if key:
                    return key
                path = str(info.get("unique_relative_path") or "").strip()
                if path:
                    return path
        except Exception:
            pass
        return needle

    def _strategy_where(self, strategy_name: str) -> tuple[str, tuple]:
        aliases = self._identity_aliases(strategy_name)
        if not aliases:
            return f"{COL_STRATEGY_KEY} = %s", ("",)
        if len(aliases) == 1:
            return f"{COL_STRATEGY_KEY} = %s", (aliases[0],)
        placeholders = ", ".join(["%s"] * len(aliases))
        return f"{COL_STRATEGY_KEY} IN ({placeholders})", tuple(aliases)

    def load_by_strategy_version(
        self, strategy_name: str, version: int
    ) -> Optional[Dict[str, Any]]:
        self._ensure_table_ready()
        where, params = self._strategy_where(strategy_name)
        row = self.load_one(
            f"{where} AND version = %s",
            tuple(list(params) + [int(version)]),
        )
        return self._normalize_row(row) if row else None

    def touch_version_updated_at(self, strategy_name: str, version: int) -> int:
        """仅刷新 ``updated_at``（V2-09 apply-settings 落盘后与会话对齐）。"""
        self._ensure_table_ready()
        current = self.load_by_strategy_version(strategy_name, version)
        if not current:
            return 0
        stored_key = str(current.get(COL_STRATEGY_KEY) or strategy_name)
        return self.execute_raw_update(
            (
                f"UPDATE {self.table_name} SET updated_at = %s "
                f"WHERE {COL_STRATEGY_KEY} = %s AND version = %s"
            ),
            (datetime.now(), stored_key, int(version)),
        )

    def list_by_strategy(self, strategy_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        self._ensure_table_ready()
        safe_limit = max(1, min(int(limit or 100), 500))
        where, params = self._strategy_where(strategy_name)
        rows = self.load(
            where,
            params,
            order_by="version DESC",
            limit=safe_limit,
        )
        return [self._normalize_row(row) for row in rows]

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(row or {})
        out[COL_SETTINGS_DIFF] = self._coerce_json_dict(out.get(COL_SETTINGS_DIFF))
        blob = self._coerce_json_dict(out.get(COL_REPORTS))
        out[COL_REPORTS] = blob
        out["result_report"] = blob
        if "version" in out:
            out["version"] = int(out.get("version") or 0)
        return out

    def get_next_version(self, strategy_name: str) -> int:
        self._ensure_table_ready()
        where, params = self._strategy_where(strategy_name)
        latest = self.load(
            where,
            params,
            order_by="version DESC",
            limit=1,
        )
        if not latest:
            return 1
        current = latest[0].get("version", 0) or 0
        return int(current) + 1

    def create_snapshot(
        self,
        strategy_name: str,
        settings_diff: Dict[str, Any],
        result_report: Optional[Dict[str, Any]] = None,
        settings_finger_print_id: str = "",
        env_fingerprint_id: str = "",
        disk_settings_hash: str = "",
    ) -> Dict[str, Any]:
        self._ensure_table_ready()
        canonical = self._canonical_strategy_key(strategy_name)
        version = self.get_next_version(strategy_name)
        now = datetime.now()
        payload = {
            COL_STRATEGY_KEY: canonical,
            "version": version,
            COL_SETTINGS_DIFF: settings_diff or {},
            COL_REPORTS: result_report or {},
            COL_SETTINGS_FP: str(settings_finger_print_id or ""),
            COL_ENV_FP: str(env_fingerprint_id or ""),
            "disk_settings_hash": str(disk_settings_hash or ""),
            "created_at": now,
            "updated_at": now,
        }
        self.upsert_one(payload, unique_keys=[COL_STRATEGY_KEY, "version"])
        return {COL_STRATEGY_KEY: canonical, "version": version}

    def update_result_report(
        self,
        strategy_name: str,
        version: int,
        result_report: Dict[str, Any],
        settings_finger_print_id: str = "",
        env_fingerprint_id: str = "",
        disk_settings_hash: str = "",
    ) -> int:
        """更新聚合 JSON（物理列 ``reports``）。"""
        self._ensure_table_ready()
        current = self.load_by_strategy_version(strategy_name, version)
        if not current:
            return 0
        canonical = self._canonical_strategy_key(strategy_name)
        stored_key = str(current.get(COL_STRATEGY_KEY) or strategy_name)
        target_settings_fp = (
            str(settings_finger_print_id)
            if settings_finger_print_id is not None and str(settings_finger_print_id) != ""
            else str(current.get(COL_SETTINGS_FP) or "")
        )
        target_env_fp = (
            str(env_fingerprint_id)
            if env_fingerprint_id is not None and str(env_fingerprint_id) != ""
            else str(current.get(COL_ENV_FP) or "")
        )
        target_disk_hash = (
            str(disk_settings_hash)
            if disk_settings_hash is not None and str(disk_settings_hash) != ""
            else str(current.get("disk_settings_hash") or "")
        )
        return self.execute_raw_update(
            (
                f"UPDATE {self.table_name} "
                f"SET {COL_STRATEGY_KEY} = %s, {COL_REPORTS} = %s, {COL_SETTINGS_FP} = %s, "
                f"{COL_ENV_FP} = %s, disk_settings_hash = %s, updated_at = %s "
                f"WHERE {COL_STRATEGY_KEY} = %s AND version = %s"
            ),
            (
                canonical,
                json.dumps(result_report or {}, ensure_ascii=False),
                target_settings_fp,
                target_env_fp,
                target_disk_hash,
                datetime.now(),
                stored_key,
                int(version),
            ),
        )

    def list_by_strategy_fingerprints(
        self,
        strategy_name: str,
        *,
        settings_finger_print_id: str = "",
        env_fingerprint_id: str = "",
        disk_settings_hash: str = "",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        按指纹列匹配。

        - 若 **同时** 传入 settings_fp 与 env_fp：**两条必须同时相等（AND）**，才是 DbCache 语义下的命中。
        - 若仅传其一：按单列相等筛选（调试或迁移脚本用途）。
        - 若传入 disk_settings_hash：**必须相等**，否则不返回缓存记录（用于检测物理文件是否被修改）。
        """
        self._ensure_table_ready()
        safe_limit = max(1, min(int(limit or 100), 500))
        settings_fp = str(settings_finger_print_id or "").strip()
        env_fp = str(env_fingerprint_id or "").strip()
        disk_hash = str(disk_settings_hash or "").strip()
        key_where, key_params = self._strategy_where(strategy_name)
        if settings_fp and env_fp:
            where = (
                f"{key_where} AND {COL_SETTINGS_FP} = %s AND {COL_ENV_FP} = %s"
            )
            params = tuple(list(key_params) + [settings_fp, env_fp])
        elif settings_fp:
            where = f"{key_where} AND {COL_SETTINGS_FP} = %s"
            params = tuple(list(key_params) + [settings_fp])
        elif env_fp:
            where = f"{key_where} AND {COL_ENV_FP} = %s"
            params = tuple(list(key_params) + [env_fp])
        else:
            return []
        if disk_hash:
            where += " AND disk_settings_hash = %s"
            params = tuple(list(params) + [disk_hash])
        rows = self.load(where, params, order_by="version DESC", limit=safe_limit)
        return [self._normalize_row(row) for row in rows]

    def delete_version_row(self, strategy_name: str, version: int) -> int:
        """删除指定策略版本行（``strategy_key`` + ``version``）。"""
        self._ensure_table_ready()
        current = self.load_by_strategy_version(strategy_name, version)
        if not current:
            return 0
        stored_key = str(current.get(COL_STRATEGY_KEY) or strategy_name)
        return self.delete_one(
            f"{COL_STRATEGY_KEY} = %s AND version = %s",
            (stored_key, int(version)),
        )

    def list_versions_asc(self, strategy_name: str, *, limit: int = 500) -> List[Dict[str, Any]]:
        """同一策略下按 ``version`` 升序（用于淘汰最早版本）。"""
        self._ensure_table_ready()
        safe_limit = max(1, min(int(limit or 500), 1000))
        where, params = self._strategy_where(strategy_name)
        rows = self.load(
            where,
            params,
            order_by="version ASC",
            limit=safe_limit,
        )
        return [self._normalize_row(row) for row in rows]
