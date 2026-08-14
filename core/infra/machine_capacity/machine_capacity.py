"""MachineInfo 门面（Facade）— infra.machine_capacity 对外统一入口类。

容量快照类型见 ``contracts.MachineCapacity``，亦可经 ``MachineInfo.types``。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from core.infra.machine_capacity.contracts import MachineCapacity

logger = logging.getLogger(__name__)

DiskType = str  # "ssd" | "hdd" | "unknown"


class TypesNamespace:
    """与 ``contracts`` 同源的类型挂载点。"""

    MachineCapacity = MachineCapacity


class MachineInfo:
    """New Tea Quant（NTQ）机器容量门面类（Facade）。"""

    types = TypesNamespace

    DEFAULT_WORKER_MEMORY_FRACTION: float = 0.85
    FALLBACK_MEMORY_FLOOR_MB: float = 2048.0
    FALLBACK_BUDGET_MB: float = 4096.0
    MIN_BUDGET_MB: float = 256.0
    MAX_BUDGET_MB: float = 16384.0
    AUTO_FLOOR_TOTAL_FRACTION: float = 0.15
    AUTO_FLOOR_AVAILABLE_FRACTION: float = 0.5
    AUTO_FLOOR_MIN_MB: float = 1024.0
    DEFAULT_RESERVE_CORES: int = 1

    @staticmethod
    def get_capacity(performance: Dict[str, Any]) -> MachineCapacity:
        """获取机器容量信息（CPU 和内存预算）。"""
        cpu_count = MachineInfo.get_cpu_count()
        reserve_cores = MachineInfo.get_reserve_cores(performance)
        memory_budget_mb, memory_floor_mb = MachineInfo.resolve_memory_budget(
            performance
        )
        return MachineCapacity(
            cpu_count=cpu_count,
            memory_budget_mb=memory_budget_mb,
            memory_floor_mb=memory_floor_mb,
            reserve_cores=reserve_cores,
        )

    @staticmethod
    def get_cpu_count() -> int:
        """获取 CPU 核心数（至少 1）。"""
        return mp.cpu_count() or 1

    @staticmethod
    def get_reserve_cores(performance: Dict[str, Any]) -> int:
        """从 ``performance.reserve_cores`` 解析预留核（默认 1）。"""
        try:
            reserve_cores = int(
                performance.get("reserve_cores", MachineInfo.DEFAULT_RESERVE_CORES)
            )
        except (TypeError, ValueError):
            reserve_cores = MachineInfo.DEFAULT_RESERVE_CORES
        return max(0, reserve_cores)

    @staticmethod
    def resolve_memory_floor(performance: Dict[str, Any]) -> float:
        """机器上必须保留的空闲内存（保底），不参与 worker 预算。"""
        raw = performance.get("memory_floor_mb")
        if raw not in (None, "", "auto"):
            return max(0.0, float(raw))

        total_mb, available_mb = MachineInfo.virtual_memory_mb()
        if total_mb is None or available_mb is None:
            return MachineInfo.FALLBACK_MEMORY_FLOOR_MB

        pct = max(
            MachineInfo.AUTO_FLOOR_MIN_MB,
            total_mb * MachineInfo.AUTO_FLOOR_TOTAL_FRACTION,
        )
        return min(
            pct,
            max(
                MachineInfo.AUTO_FLOOR_MIN_MB,
                available_mb * MachineInfo.AUTO_FLOOR_AVAILABLE_FRACTION,
            ),
        )

    @staticmethod
    def resolve_memory_budget(performance: Dict[str, Any]) -> Tuple[float, float]:
        """返回 ``(worker 可用预算 MB, memory_floor_mb)``。"""
        floor_mb = MachineInfo.resolve_memory_floor(performance)
        raw = performance.get("memory_budget_mb")
        if raw not in ("auto", None, ""):
            return max(MachineInfo.MIN_BUDGET_MB, float(raw)), floor_mb

        _total_mb, available_mb = MachineInfo.virtual_memory_mb()
        if available_mb is None:
            return MachineInfo.FALLBACK_BUDGET_MB, floor_mb

        usable = max(0.0, available_mb - floor_mb)
        try:
            fraction = float(
                performance.get(
                    "worker_memory_fraction",
                    MachineInfo.DEFAULT_WORKER_MEMORY_FRACTION,
                )
            )
        except (TypeError, ValueError):
            fraction = MachineInfo.DEFAULT_WORKER_MEMORY_FRACTION
        fraction = max(0.1, min(1.0, fraction))
        budget = usable * fraction
        return (
            max(MachineInfo.MIN_BUDGET_MB, min(budget, MachineInfo.MAX_BUDGET_MB)),
            floor_mb,
        )

    @staticmethod
    def get_available_workers(capacity: MachineCapacity) -> int:
        """可用 worker 数：``cpu_count − reserve_cores``（至少 1）。"""
        return max(1, capacity.cpu_count - capacity.reserve_cores)

    @staticmethod
    def worker_pool_budget_mb(capacity: MachineCapacity) -> float:
        """进程池并发可用的内存预算（MB）；至少 1。"""
        return max(1.0, float(capacity.memory_budget_mb))

    @staticmethod
    def parse_max_parallel_jobs_cap(raw: Any) -> Optional[int]:
        """解析并行 job 上限；``None`` / 空 / ``\"null\"`` / 非法 → ``None``。"""
        if raw in (None, "", "null", "auto"):
            return None
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def virtual_memory_mb() -> Tuple[Optional[float], Optional[float]]:
        """本机 ``(total_mb, available_mb)``；无 psutil 或读取失败时返回 ``(None, None)``。"""
        try:
            import psutil
        except ImportError:
            return None, None
        try:
            vm = psutil.virtual_memory()
            total = float(vm.total) / (1024.0 * 1024.0)
            available = float(vm.available) / (1024.0 * 1024.0)
            return total, available
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            logger.debug("virtual_memory_mb unavailable: %s", exc)
            return None, None

    @staticmethod
    def get_disk_type(path: Optional[Union[str, Path]] = None) -> DiskType:
        """探测 ``path`` 所在卷的介质：``ssd`` / ``hdd`` / ``unknown``。

        ``path`` 默认当前工作目录。探测失败或无法判定时返回 ``unknown``。
        """
        try:
            target = MachineInfo._resolve_probe_path(path)
            system = (platform.system() or "").lower()
            if system == "linux":
                return MachineInfo._disk_type_linux(target)
            if system == "darwin":
                return MachineInfo._disk_type_darwin(target)
            if system == "windows":
                return MachineInfo._disk_type_windows(target)
            return "unknown"
        except Exception as exc:
            logger.debug("get_disk_type failed: %s", exc)
            return "unknown"

    @staticmethod
    def _resolve_probe_path(path: Optional[Union[str, Path]]) -> Path:
        if path is None or str(path).strip() == "":
            return Path.cwd().resolve()
        p = Path(path).expanduser()
        try:
            if p.exists():
                return p.resolve()
        except OSError:
            pass
        return Path.cwd().resolve()

    @staticmethod
    def _longest_mount_for(path: Path) -> Optional[Any]:
        try:
            import psutil
        except ImportError:
            return None
        try:
            needle = str(path.resolve())
        except OSError:
            needle = str(path)
        best = None
        best_len = -1
        for part in psutil.disk_partitions(all=False):
            mount = str(part.mountpoint or "")
            if not mount:
                continue
            if needle == mount or needle.startswith(mount.rstrip("/\\") + os.sep):
                if len(mount) > best_len:
                    best = part
                    best_len = len(mount)
        return best

    @staticmethod
    def _disk_type_linux(path: Path) -> DiskType:
        part = MachineInfo._longest_mount_for(path)
        device = str(getattr(part, "device", "") or "")
        name = MachineInfo._linux_block_name(device)
        if not name:
            return "unknown"
        rotational = Path(f"/sys/block/{name}/queue/rotational")
        try:
            raw = rotational.read_text(encoding="utf-8").strip()
        except OSError:
            return "unknown"
        if raw == "0":
            return "ssd"
        if raw == "1":
            return "hdd"
        return "unknown"

    @staticmethod
    def _linux_block_name(device: str) -> str:
        """``/dev/sda1`` / ``/dev/nvme0n1p2`` → sysfs block 名；mapper/loop/md → 空。"""
        dev = str(device or "").strip()
        if not dev.startswith("/dev/"):
            return ""
        if "/mapper/" in dev or "/loop" in dev:
            return ""
        base = Path(dev).name
        if base.startswith("nvme") and "p" in base:
            return re.sub(r"p\d+$", "", base)
        if re.match(r"^.+\d+$", base) and not base.startswith("nvme"):
            return re.sub(r"\d+$", "", base)
        if base.startswith(("dm-", "loop", "md")):
            return ""
        return base

    @staticmethod
    def _disk_type_darwin(path: Path) -> DiskType:
        try:
            proc = subprocess.run(
                ["diskutil", "info", str(path)],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return "unknown"
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        for line in text.splitlines():
            if "Solid State" in line or "SolidState" in line.replace(" ", ""):
                low = line.lower()
                if "yes" in low or "true" in low:
                    return "ssd"
                if "no" in low or "false" in low:
                    return "hdd"
        if re.search(r"Protocol:\s*Apple Fabric|Protocol:\s*PCI-Express|NVMe", text):
            return "ssd"
        return "unknown"

    @staticmethod
    def _disk_type_windows(path: Path) -> DiskType:
        try:
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-PhysicalDisk | Select-Object -ExpandProperty MediaType) -join ','",
                ],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return "unknown"
        text = (proc.stdout or "").strip().lower()
        if not text:
            return "unknown"
        kinds = {p.strip() for p in text.split(",") if p.strip()}
        if kinds == {"ssd"}:
            return "ssd"
        if kinds == {"hdd"}:
            return "hdd"
        if "ssd" in kinds and "hdd" not in kinds:
            return "ssd"
        if "hdd" in kinds and "ssd" not in kinds:
            return "hdd"
        return "unknown"


__all__ = ["MachineInfo"]
