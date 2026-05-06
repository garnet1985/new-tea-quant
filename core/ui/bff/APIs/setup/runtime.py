from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.infra.project_context.path_manager import PathManager
from setup.meta_loader import load_setup_step_meta

REPO_ROOT = Path(__file__).resolve().parents[5]
STATE_FILE = REPO_ROOT / ".ntq" / "setup-runtime.json"


class SetupRuntimeManager:
    STATUS_NOT_STARTED = "not_started"
    STATUS_WAITING_INPUT = "waiting_input"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def get_definition(self) -> List[Dict[str, Any]]:
        return load_setup_step_meta(ui_only=True)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            current = self._load_state()
            return self._build_snapshot(current)

    def start(self) -> Dict[str, Any]:
        definition = self.get_definition()
        state = self._new_state(definition)
        self._save_state(state)
        return self._run_pipeline(state)

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            definition = self.get_definition()
            state = self._new_state(definition)
            self._save_state(state)
            return {"status": "ok", "message": self._build_snapshot(state)}

    def submit(self, step_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        state = self._load_state()
        definition = self.get_definition()
        by_id = {s["id"]: s for s in definition}
        step = by_id.get(step_id)
        if not step:
            return self._error("SETUP_STEP_NOT_FOUND", f"未知步骤: {step_id}")

        state["inputsByStep"][step_id] = inputs or {}
        self._bump_version(state)
        self._save_state(state)
        return self._run_pipeline(state, force_step_id=step_id)

    def retry(self) -> Dict[str, Any]:
        definition = self.get_definition()
        state = self._new_state(definition)
        self._save_state(state)
        return self._run_pipeline(state)

    def precheck_db_connection(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        payload = inputs or {}
        db_type = str(payload.get("dbType", "")).strip().lower()
        db_name = str(payload.get("database", "")).strip()
        exists = self._db_exists_precheck(payload)
        return {
            "status": "ok",
            "message": {
                "dbExists": bool(exists),
                "dbType": db_type,
                "database": db_name,
            },
        }

    def precheck_userspace_path(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        payload = inputs or {}
        raw_target = str(payload.get("userspaceTargetPath", "")).strip()
        if raw_target:
            target = Path(raw_target).expanduser()
        else:
            target = PathManager.userspace()

        exists = target.exists()
        return {
            "status": "ok",
            "message": {
                "userspacePath": str(target.resolve()),
                "pathExists": bool(exists),
            },
        }

    def get_import_data_progress(self) -> Dict[str, Any]:
        progress_file = REPO_ROOT / "setup" / "init_data" / ".import_progress.json"
        if not progress_file.is_file():
            return {
                "status": "ok",
                "message": {
                    "running": False,
                    "totalTables": 0,
                    "completedCount": 0,
                    "currentTable": "",
                    "percent": 0,
                    "updatedAt": 0,
                },
            }
        try:
            payload = json.loads(progress_file.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

        completed_tables = payload.get("completed_tables", {}) or {}
        total_tables = int(payload.get("total_tables") or 0)
        if total_tables <= 0:
            order = payload.get("table_order", []) or []
            if isinstance(order, list) and order:
                total_tables = len(order)
            else:
                total_tables = max(len(completed_tables), 1)

        completed_count = sum(1 for v in completed_tables.values() if v == "done")
        current_table = str(payload.get("in_progress_table") or "")
        running = bool(current_table) or completed_count < total_tables
        percent = int(round((completed_count / total_tables) * 100)) if total_tables > 0 else 0
        return {
            "status": "ok",
            "message": {
                "running": running,
                "totalTables": total_tables,
                "completedCount": completed_count,
                "currentTable": current_table,
                "percent": max(0, min(percent, 100)),
                "updatedAt": int(payload.get("updated_at") or 0),
            },
        }

    def _run_pipeline(self, state: Dict[str, Any], force_step_id: Optional[str] = None) -> Dict[str, Any]:
        definition = self.get_definition()
        by_id = {s["id"]: s for s in definition}
        ordered_ids = [s["id"] for s in definition]

        if force_step_id and force_step_id in by_id:
            idx = ordered_ids.index(force_step_id)
            next_ids = ordered_ids[idx:]
        else:
            next_ids = ordered_ids

        for step_id in next_ids:
            step = by_id[step_id]
            cur = self._get_step_state(state, step_id)
            if cur == self.STATUS_SUCCESS:
                continue

            if bool(step.get("requiresUserInput")) and step_id not in state.get("inputsByStep", {}):
                self._set_step_state(state, step_id, self.STATUS_WAITING_INPUT, "")
                self._bump_version(state)
                self._save_state(state)
                return {
                    "status": "ok",
                    "message": {
                        "kind": "paused",
                        "pausedStepId": step_id,
                        "snapshot": self._build_snapshot(state),
                    },
                }

            ok, err = self._execute_step(state, step)
            self._bump_version(state)
            self._save_state(state)
            if not ok:
                return {
                    "status": "ok",
                    "message": {
                        "kind": "failed",
                        "failedStepId": step_id,
                        "errorMessage": err,
                        "snapshot": self._build_snapshot(state),
                    },
                }

        state["isReady"] = all(self._get_step_state(state, s["id"]) == self.STATUS_SUCCESS for s in definition)
        self._bump_version(state)
        self._save_state(state)
        return {
            "status": "ok",
            "message": {
                "kind": "completed",
                "snapshot": self._build_snapshot(state),
            },
        }

    def _execute_step(self, state: Dict[str, Any], step: Dict[str, Any]) -> Tuple[bool, str]:
        step_id = step["id"]
        self._set_step_state(state, step_id, self.STATUS_RUNNING, "")
        self._save_state(state)

        try:
            step_inputs = state.get("inputsByStep", {}).get(step_id, {}) or {}
            db_existed_before = None
            if step_id == "db_connection":
                db_existed_before = self._db_exists_precheck(step_inputs)

            self._prepare_inputs_for_step(state, step_id, step_inputs)
            script_rel = str(step.get("scriptEntry", "")).strip()
            if not script_rel:
                self._set_step_state(state, step_id, self.STATUS_FAILED, "缺少 scriptEntry")
                return False, "缺少 scriptEntry"
            script = (REPO_ROOT / script_rel).resolve()
            if not script.is_file():
                self._set_step_state(state, step_id, self.STATUS_FAILED, f"脚本不存在: {script_rel}")
                return False, f"脚本不存在: {script_rel}"

            env = os.environ.copy()
            if step_id == "init_userspace":
                step_inputs = state.get("inputsByStep", {}).get(step_id, {}) or {}
                target = str(step_inputs.get("userspaceTargetPath", "")).strip()
                if target:
                    env["NTQ_USERSPACE_TARGET_PATH"] = target
                policy = str(step_inputs.get("userspaceConflictPolicy", "skip")).strip().lower() or "skip"
                if policy not in ("skip", "overwrite"):
                    policy = "skip"
                env["NTQ_USERSPACE_CONFLICT_POLICY"] = policy

            proc = subprocess.run(
                [sys_executable(), str(script)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                msg = (proc.stderr or proc.stdout or "").strip()[-600:] or f"{step_id} 执行失败"
                self._set_step_state(state, step_id, self.STATUS_FAILED, msg)
                return False, msg

            notices = state.setdefault("noticesByStep", {})
            if step_id == "db_connection":
                combined_output = f"{proc.stdout or ''}\n{proc.stderr or ''}"
                output_indicates_exists = (
                    "已存在（跳过创建）" in combined_output
                    or "数据库" in combined_output and "已存在" in combined_output
                )
                db_type = str(step_inputs.get("dbType", "")).strip().lower()
                db_name = str(step_inputs.get("database", "")).strip()
                if db_existed_before is True or output_indicates_exists:
                    name_text = f"{db_type}:{db_name}" if db_name else "当前目标数据库"
                    notices[step_id] = f"检测到 {name_text} 已存在：后续初始化数据导入可能覆盖部分表数据，请确认后继续。"
                else:
                    notices.pop(step_id, None)

            self._set_step_state(state, step_id, self.STATUS_SUCCESS, "")
            if step_id == "init_userspace":
                PathManager.invalidate_userspace_cache()
            return True, ""
        except Exception as e:  # pragma: no cover
            msg = str(e)
            self._set_step_state(state, step_id, self.STATUS_FAILED, msg)
            return False, msg

    def _resolve_userspace_root(self, state: Dict[str, Any]) -> Path:
        init_inputs = (state.get("inputsByStep", {}) or {}).get("init_userspace", {}) or {}
        init_target = str(init_inputs.get("userspaceTargetPath", "")).strip()
        if init_target:
            return Path(init_target).expanduser().resolve()
        return PathManager.userspace()

    def _prepare_inputs_for_step(self, state: Dict[str, Any], step_id: str, inputs: Dict[str, Any]) -> None:
        if step_id != "db_connection":
            return
        db_type = str((inputs or {}).get("dbType", "postgresql")).strip().lower() or "postgresql"
        if db_type not in ("postgresql", "mysql"):
            db_type = "postgresql"

        userspace_root = self._resolve_userspace_root(state)
        db_cfg_dir = userspace_root / "config" / "database"
        db_cfg_dir.mkdir(parents=True, exist_ok=True)

        common_json = db_cfg_dir / "common.json"
        common_payload = {"database_type": db_type}
        common_json.write_text(json.dumps(common_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        detail_json = db_cfg_dir / f"{db_type}.json"
        wrapper: Dict[str, Any] = {
            db_type: {
                "host": (inputs or {}).get("host", ""),
                "port": int((inputs or {}).get("port", 5432 if db_type == "postgresql" else 3306)),
                "database": (inputs or {}).get("database", ""),
                "user": (inputs or {}).get("user", ""),
                "password": (inputs or {}).get("password", ""),
            }
        }
        if db_type == "postgresql":
            wrapper[db_type]["default_pgsql_schema"] = (inputs or {}).get("defaultPgsqlSchema", "public") or "public"
        detail_json.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2), encoding="utf-8")

    def _new_state(self, definition: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "sessionId": f"setup_{int(time.time())}",
            "version": 1,
            "isReady": False,
            "stepStates": [
                {"stepId": step["id"], "status": self.STATUS_NOT_STARTED, "errorMessage": ""}
                for step in definition
            ],
            "inputsByStep": {},
            "noticesByStep": {},
        }

    def _build_snapshot(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "sessionId": state.get("sessionId", ""),
            "version": int(state.get("version", 1)),
            "isReady": bool(state.get("isReady", False)),
            "stepStates": state.get("stepStates", []),
            "inputsByStep": state.get("inputsByStep", {}),
            "noticesByStep": state.get("noticesByStep", {}),
        }

    def _load_state(self) -> Dict[str, Any]:
        if not STATE_FILE.is_file():
            return self._new_state(self.get_definition())
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return self._new_state(self.get_definition())

    def _save_state(self, state: Dict[str, Any]) -> None:
        with self._lock:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _set_step_state(self, state: Dict[str, Any], step_id: str, status: str, err: str) -> None:
        for item in state.get("stepStates", []):
            if item.get("stepId") == step_id:
                item["status"] = status
                item["errorMessage"] = err
                return

    def _get_step_state(self, state: Dict[str, Any], step_id: str) -> str:
        for item in state.get("stepStates", []):
            if item.get("stepId") == step_id:
                return str(item.get("status", self.STATUS_NOT_STARTED))
        return self.STATUS_NOT_STARTED

    def _bump_version(self, state: Dict[str, Any]) -> None:
        state["version"] = int(state.get("version", 1)) + 1

    def _db_exists_precheck(self, inputs: Dict[str, Any]) -> Optional[bool]:
        db_type = str((inputs or {}).get("dbType", "postgresql")).strip().lower() or "postgresql"
        host = str((inputs or {}).get("host", "localhost")).strip() or "localhost"
        user = str((inputs or {}).get("user", "")).strip()
        password = str((inputs or {}).get("password", ""))
        database = str((inputs or {}).get("database", "")).strip()
        if not database or not user:
            return None

        try:
            if db_type == "postgresql":
                import psycopg2

                try:
                    conn = psycopg2.connect(
                        host=host,
                        port=int((inputs or {}).get("port", 5432)),
                        database="postgres",
                        user=user,
                        password=password,
                    )
                except Exception:
                    conn = psycopg2.connect(
                        host=host,
                        port=int((inputs or {}).get("port", 5432)),
                        database="template1",
                        user=user,
                        password=password,
                    )
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
                        return cur.fetchone() is not None
                finally:
                    conn.close()

            if db_type == "mysql":
                import pymysql

                conn = pymysql.connect(
                    host=host,
                    port=int((inputs or {}).get("port", 3306)),
                    user=user,
                    password=password,
                    charset="utf8mb4",
                    autocommit=True,
                )
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s",
                            (database,),
                        )
                        return cur.fetchone() is not None
                finally:
                    conn.close()
        except Exception:
            return None
        return None

    @staticmethod
    def _error(code: str, detail: str) -> Dict[str, Any]:
        return {"status": "error", "message": {"code": code, "detail": detail}}


def sys_executable() -> str:
    return os.environ.get("PYTHON_EXECUTABLE", sys.executable)
