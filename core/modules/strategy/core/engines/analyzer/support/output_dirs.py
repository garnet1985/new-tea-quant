"""Resolve simulation step output directories on disk."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.services.artifacts import ArtifactStore


class SimulationOutputDirs:
    @staticmethod
    def _version_dir_candidates_from_slot(
        slot: Dict[str, Any], workbench_version: int = 0
    ) -> List[str]:
        dirs: List[str] = []

        out_d = str(slot.get("output_dir") or "").strip()
        if out_d:
            dirs.append(out_d)

        vid = slot.get("version_id")
        if vid is not None:
            try:
                dirs.append(str(int(vid)))
            except (TypeError, ValueError):
                text = str(vid).strip()
                if text:
                    dirs.append(text)

        if workbench_version > 0:
            dirs.append(str(int(workbench_version)))

        seen: set[str] = set()
        uniq: List[str] = []
        for d in dirs:
            if d and d not in seen:
                seen.add(d)
                uniq.append(d)
        return uniq

    @classmethod
    def resolve(
        cls,
        strategy_name: str,
        *,
        step: str,
        slot: Optional[Dict[str, Any]] = None,
        workbench_version: int = 0,
    ) -> List[Path]:
        sn = str(strategy_name or "").strip()
        if not sn:
            return []

        slot = slot if isinstance(slot, dict) else {}
        names = cls._version_dir_candidates_from_slot(slot, workbench_version)
        try:
            from core.modules.strategy import Strategy

            folder = Strategy.resolve_folder(sn)
            kind = ArtifactStore.parse_kind(step)
        except ValueError:
            return []
        root = ArtifactStore.simulations_root(folder)
        step_dir = ArtifactStore.for_kind(kind).step_dir_name()

        out: List[Path] = []
        seen: set[str] = set()
        for name in names:
            p = Path(name)
            if not p.is_absolute():
                p = root / name / step_dir
            key = str(p)
            if key not in seen:
                seen.add(key)
                out.append(p)
        return out
