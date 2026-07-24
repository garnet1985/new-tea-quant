"""模拟 run 产物 version 目录分配与跨进程 snapshot。

本文件:
- SimulationOutputRecorder: 分配 ``simulation/{kind}/{strategy}/{version}``、meta.json 递增
  边界: 负责目录与 snapshot 序列化；不负责 report 内容写盘（各 ReportManager）
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="SimulationOutputRecorder")


def _read_next_output_version(meta: Dict[str, Any]) -> int:
    try:
        return max(int(meta.get("next_output_version") or 1), 1)
    except (TypeError, ValueError):
        return 1


@dataclass
class SimulationOutputRecorder:
    """模拟 run 输出基类：绑定 output_dir / version，支持 snapshot 跨进程传递。"""

    output_dir: Path
    strategy_id: str
    version_id: int
    version_dir_name: str

    SNAPSHOT_KEY: str = "output_recorder"
    INSTANCE_KEY: str = "_output_recorder"

    # ── version 目录分配（子类传入 simulation root）──

    @classmethod
    def allocate_version_dir(
        cls,
        strategy_id: str,
        simulation_root: Path,
    ) -> Tuple[Path, int]:
        simulation_root.mkdir(parents=True, exist_ok=True)
        meta_path = simulation_root / "meta.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        else:
            meta = {}

        version_id = _read_next_output_version(meta)
        version_dir = simulation_root / str(version_id)
        version_dir.mkdir(parents=True, exist_ok=True)

        meta["next_output_version"] = version_id + 1
        meta["last_updated"] = datetime.now().isoformat()
        meta["strategy_name"] = strategy_id
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Allocated simulation version: %s (id=%d)", version_dir, version_id)
        return version_dir, version_id

    # ── 跨进程 context ──

    def to_snapshot(self) -> Dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "strategy_id": self.strategy_id,
            "version_id": self.version_id,
            "version_dir_name": self.version_dir_name,
        }

    @classmethod
    def from_snapshot(cls: Type[T], snapshot: Dict[str, Any]) -> T:
        return cls(
            output_dir=Path(str(snapshot["output_dir"])),
            strategy_id=str(snapshot["strategy_id"]),
            version_id=int(snapshot["version_id"]),
            version_dir_name=str(snapshot["version_dir_name"]),
        )

    @classmethod
    def resolve(cls: Type[T], payload: Dict[str, Any]) -> T:
        """子进程内：从 payload 还原 recorder（同一 job 内复用实例）。"""
        cached = payload.get(cls.INSTANCE_KEY)
        if isinstance(cached, cls):
            return cached

        snapshot = payload.get(cls.SNAPSHOT_KEY)
        if not isinstance(snapshot, dict):
            raise ValueError(f"payload 缺少 {cls.SNAPSHOT_KEY} snapshot")

        recorder = cls.from_snapshot(snapshot)
        payload[cls.INSTANCE_KEY] = recorder
        return recorder


__all__ = ["SimulationOutputRecorder"]
