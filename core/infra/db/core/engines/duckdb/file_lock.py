"""DuckDB 文件锁占用排查与清理。

同一 ``.duckdb`` 同时只能有一个写进程。开发时常见：未退出的 ``python -c`` /
卡死 CLI 占着 ``userspace/system/db/*.duckdb``，导致 launcher / agent 无法打开库。

本模块只做进程级排查（``lsof``），不删 ``.wal``、不改库内容。
"""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from core.infra.project_context import ProjectContext

_SYSTEM_CMD_MARKERS = (
    "fileprovider",
    "mds_stores",
    "spotlight",
    "corespotlightd",
    "cloudd",
)
_ACTIVE_APP_MARKERS = (
    "launcher.py",
    "core/bff",
    "core.bff",
    "uvicorn",
)


class DuckdbFileLock:
    """列出 / 结束占用 ``userspace/system/db/*.duckdb`` 的进程。"""

    @classmethod
    def db_dir(cls) -> Path:
        return Path(ProjectContext.path.get_system_db_directory()).resolve()

    @classmethod
    def duckdb_files(cls, db_dir: Optional[Path] = None) -> List[Path]:
        root = Path(db_dir or cls.db_dir())
        if not root.is_dir():
            return []
        return sorted(p.resolve() for p in root.glob("*.duckdb") if p.is_file())

    @classmethod
    def inspect(cls, *, db_dir: Optional[Path] = None) -> Dict[str, Any]:
        """只读：列出占用各 ``.duckdb`` 的进程。"""
        root = Path(db_dir or cls.db_dir())
        files = cls.duckdb_files(root)
        holders = cls._holders_for_files(files)
        self_pid = os.getpid()
        for row in holders:
            cls._annotate(row, self_pid=self_pid)
        return {
            "ok": True,
            "db_dir": str(root),
            "files": [str(p) for p in files],
            "holders": holders,
            "self_pid": self_pid,
            "blocked": any(
                h.get("kind") in {"stale_candidate", "active_app", "other"}
                for h in holders
            ),
            "note": (
                "同一 DuckDB 文件同时只能一个写进程。"
                "清理请用 release(kill=True)；默认不杀 launcher/BFF。"
            ),
        }

    @classmethod
    def release(
        cls,
        *,
        kill: bool = False,
        force: bool = False,
        db_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """排查占用；``kill=True`` 时结束可清理进程。

        - 默认只杀 ``stale_candidate``（如卡死的 ``python -c``）
        - ``force=True`` 才允许杀 ``active_app``（launcher / BFF）
        - 永不杀本进程与系统文件服务
        """
        report = cls.inspect(db_dir=db_dir)
        holders = list(report.get("holders") or [])
        if not kill:
            report["killed"] = []
            report["skipped"] = [
                {
                    "pid": h.get("pid"),
                    "kind": h.get("kind"),
                    "reason": "kill=false，仅列出",
                }
                for h in holders
            ]
            return report

        killed: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        seen: Set[int] = set()
        for row in holders:
            pid = int(row.get("pid") or 0)
            if pid <= 0 or pid in seen:
                continue
            seen.add(pid)
            kind = str(row.get("kind") or "")
            if kind in {"self", "system"}:
                skipped.append(
                    {"pid": pid, "kind": kind, "reason": "受保护，不杀"}
                )
                continue
            if kind == "active_app" and not force:
                skipped.append(
                    {
                        "pid": pid,
                        "kind": kind,
                        "reason": "活跃应用；若确需结束请 force=true",
                    }
                )
                continue
            if kind not in {"stale_candidate", "active_app", "other"}:
                skipped.append(
                    {"pid": pid, "kind": kind, "reason": "未知类型，跳过"}
                )
                continue
            err = cls._terminate(pid)
            if err:
                skipped.append({"pid": pid, "kind": kind, "reason": err})
            else:
                killed.append(
                    {
                        "pid": pid,
                        "kind": kind,
                        "command": row.get("command"),
                    }
                )

        # 再扫一次确认
        after = cls.inspect(db_dir=db_dir)
        return {
            "ok": True,
            "db_dir": report.get("db_dir"),
            "files": report.get("files"),
            "holders_before": holders,
            "killed": killed,
            "skipped": skipped,
            "holders_after": after.get("holders") or [],
            "blocked_after": bool(after.get("blocked")),
            "note": after.get("note"),
        }

    @classmethod
    def _holders_for_files(cls, files: Sequence[Path]) -> List[Dict[str, Any]]:
        if not files:
            return []
        try:
            proc = subprocess.run(
                ["lsof", "-nP", *[str(p) for p in files]],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except FileNotFoundError:
            return [
                {
                    "pid": 0,
                    "command": "",
                    "error": "本机没有 lsof，无法自动排查文件锁",
                    "kind": "error",
                }
            ]
        except Exception as exc:  # noqa: BLE001
            return [
                {
                    "pid": 0,
                    "command": "",
                    "error": f"lsof 失败: {exc}",
                    "kind": "error",
                }
            ]

        out: List[Dict[str, Any]] = []
        seen: Set[tuple] = set()
        for line in (proc.stdout or "").splitlines():
            if line.startswith("COMMAND") or not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            command_name = parts[0]
            try:
                pid = int(parts[1])
            except ValueError:
                continue
            path = parts[-1] if parts else ""
            key = (pid, path)
            if key in seen:
                continue
            seen.add(key)
            full_cmd = cls._command_for_pid(pid) or command_name
            out.append(
                {
                    "pid": pid,
                    "command": full_cmd,
                    "short_command": command_name,
                    "path": path,
                }
            )
        return out

    @staticmethod
    def _command_for_pid(pid: int) -> str:
        try:
            proc = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return (proc.stdout or "").strip()
        except Exception:  # noqa: BLE001
            return ""

    @classmethod
    def _annotate(cls, row: Dict[str, Any], *, self_pid: int) -> None:
        pid = int(row.get("pid") or 0)
        cmd = str(row.get("command") or row.get("short_command") or "")
        low = cmd.lower()
        if pid == self_pid:
            row["kind"] = "self"
            row["killable"] = False
            return
        if any(marker in low for marker in _SYSTEM_CMD_MARKERS):
            row["kind"] = "system"
            row["killable"] = False
            return
        if any(marker in low for marker in _ACTIVE_APP_MARKERS):
            row["kind"] = "active_app"
            row["killable"] = True  # 仅 force
            return
        if "python" in low:
            row["kind"] = "stale_candidate"
            row["killable"] = True
            return
        row["kind"] = "other"
        row["killable"] = True

    @staticmethod
    def _terminate(pid: int) -> str:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return ""
        except PermissionError:
            return "无权限 SIGTERM"
        except Exception as exc:  # noqa: BLE001
            return f"SIGTERM 失败: {exc}"

        # 短暂等待后仍在则 SIGKILL
        try:
            import time

            time.sleep(0.4)
            os.kill(pid, 0)
        except ProcessLookupError:
            return ""
        except Exception:  # noqa: BLE001
            return ""

        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            return ""
        except PermissionError:
            return "无权限 SIGKILL"
        except Exception as exc:  # noqa: BLE001
            return f"SIGKILL 失败: {exc}"
        return ""


__all__ = ["DuckdbFileLock"]
