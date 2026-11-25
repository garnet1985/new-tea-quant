"""设置页导入数据：经 JobPipeline 后台下载并导入。"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional

from core.infra.job_pipeline import JobPipeline
from core.infra.job_pipeline.contracts import JobRunningBusyError

logger = logging.getLogger(__name__)

IMPORT_DATA_RESOURCE = "import_data"


class ImportDataLauncher:
    """后台下载 + 导入初始化数据包。"""

    _LOCK = threading.Lock()
    _ACTIVE: Optional[Dict[str, Any]] = None

    @classmethod
    def trigger(cls, *, pack_kind: str = "demo", force: bool = False) -> Dict[str, Any]:
        kind = str(pack_kind or "demo").strip().lower() or "demo"
        label = (
            "导入会员数据包（全 A × 三年）"
            if kind == "member"
            else "导入演示数据包（约 300 股 × 三年）"
        )
        return JobPipeline.submit(
            {
                "kind": "import_data",
                "resource_key": IMPORT_DATA_RESOURCE,
                "label": label,
                "domains": ["data", "setup"],
                "payload": {"pack_kind": kind, "force": bool(force)},
            }
        )

    @classmethod
    def start_now(
        cls,
        *,
        pack_kind: str = "demo",
        force: bool = False,
    ) -> Dict[str, Any]:
        kind = str(pack_kind or "demo").strip().lower() or "demo"
        with cls._LOCK:
            if cls._running_locked():
                return {
                    "is_triggered": False,
                    "reason": "已有数据导入任务在运行，请稍后再试",
                }
            job_id = f"import-data-{uuid.uuid4().hex[:12]}"
            cls._ACTIVE = {
                "job_id": job_id,
                "pack_kind": kind,
                "running": True,
                "error": "",
                "message": "",
            }

        thread = threading.Thread(
            target=cls._background,
            args=(job_id, kind, bool(force)),
            daemon=True,
            name=f"import-data-{job_id[-8:]}",
        )
        thread.start()
        return {
            "is_triggered": True,
            "job_id": job_id,
            "pack_kind": kind,
            "running": True,
            "queued": False,
        }

    @classmethod
    def status(cls) -> Dict[str, Any]:
        with cls._LOCK:
            active = dict(cls._ACTIVE or {})
        if not active:
            running = JobPipeline.get_running_job()
            if running and str(running.get("kind") or "") == "import_data":
                return {
                    "running": True,
                    "job_id": str(running.get("job_id") or ""),
                    "pack_kind": "",
                    "error": "",
                    "message": "",
                }
            return {
                "running": False,
                "job_id": "",
                "pack_kind": "",
                "error": "",
                "message": "",
            }
        return {
            "running": bool(active.get("running")),
            "job_id": str(active.get("job_id") or ""),
            "pack_kind": str(active.get("pack_kind") or ""),
            "error": str(active.get("error") or ""),
            "message": str(active.get("message") or ""),
        }

    @classmethod
    def _running_locked(cls) -> bool:
        return bool(cls._ACTIVE and cls._ACTIVE.get("running"))

    @classmethod
    def _background(cls, job_id: str, pack_kind: str, force: bool) -> None:
        lease = JobPipeline.running_lease(
            kind="import_data",
            job_id=job_id,
            resource_key=IMPORT_DATA_RESOURCE,
            label=(
                "导入会员数据包（全 A × 三年）"
                if pack_kind == "member"
                else "导入演示数据包（约 300 股 × 三年）"
            ),
            domains=["data", "setup"],
        )
        acquired = False
        try:
            lease.acquire()
            acquired = True
        except JobRunningBusyError as exc:
            cls._finish(job_id, str(exc))
            cls._notify_finished()
            return
        try:
            if JobPipeline.is_cancel_requested(job_id):
                cls._finish(job_id, "用户取消")
                return
            try:
                from core.bff.APIs.platform.setup.runtime import SetupRuntimeManager

                # 实例方法，临时构造以复用释放逻辑。
                SetupRuntimeManager()._release_bff_duckdb_for_setup_subprocess()
            except Exception:
                logger.debug("release duckdb before import failed", exc_info=True)

            from core.infra.setup import Setup

            Setup.runtime.import_data_pack(
                pack_kind=pack_kind,
                force=force,
                remove_extract=True,
            )
            cls._finish(job_id, "", message="导入完成")
        except Exception as exc:  # noqa: BLE001
            logger.exception("import_data job failed job_id=%s", job_id)
            cls._finish(
                job_id,
                str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__,
            )
        finally:
            if acquired:
                lease.release()
            cls._notify_finished()

    @staticmethod
    def _notify_finished() -> None:
        try:
            JobPipeline.notify_job_finished()
        except Exception:
            logger.exception("JobPipeline.notify_job_finished after import failed")

    @classmethod
    def _finish(cls, job_id: str, error: str, message: str = "") -> None:
        with cls._LOCK:
            active = cls._ACTIVE
            if not active or active.get("job_id") != job_id:
                return
            active["running"] = False
            active["error"] = error
            active["message"] = message
