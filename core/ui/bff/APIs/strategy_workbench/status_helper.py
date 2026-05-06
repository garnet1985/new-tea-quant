"""Run-status helper for strategy workbench."""

from datetime import datetime
import json
from uuid import uuid4

from core.infra.project_context.path_manager import PathManager
from core.ui.bff.shared.file_ops import atomic_write_text
from core.ui.bff.shared.response import error


class StrategyWorkbenchStatusHelper:
    """Shared helpers for run id + status file IO/CAS."""

    @staticmethod
    def _build_run_id() -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"run_{stamp}_{uuid4().hex[:6]}"

    @staticmethod
    def _status_file(strategy_name: str):
        return PathManager.userspace() / ".ntq" / "tmp" / "strategy-workbench" / f"{strategy_name}.json"

    @staticmethod
    def _read_status(strategy_name: str):
        path = StrategyWorkbenchStatusHelper._status_file(strategy_name)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and "_revision" not in payload:
                payload["_revision"] = 0
            return payload
        except Exception:
            return None

    @staticmethod
    def _write_status(strategy_name: str, payload: dict) -> None:
        path = StrategyWorkbenchStatusHelper._status_file(strategy_name)
        current = StrategyWorkbenchStatusHelper._read_status(strategy_name) or {}
        current_revision = int(current.get("_revision") or 0)
        expected_revision = int(payload.get("_revision") or current_revision)
        if expected_revision != current_revision:
            merged = dict(current)
            merged.update(payload or {})
            payload = merged
        payload["_revision"] = current_revision + 1
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        atomic_write_text(path, content)

    @staticmethod
    def _require_status_for_run(strategy_name: str, run_id: str):
        status_payload = StrategyWorkbenchStatusHelper._read_status(strategy_name)
        if not isinstance(status_payload, dict):
            return None, error(f"未找到运行记录: {run_id}", 404)
        if str(status_payload.get("run_id") or "") != str(run_id):
            return None, error(f"未找到运行记录: {run_id}", 404)
        return status_payload, None