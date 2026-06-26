#!/usr/bin/env python3
"""磁盘模拟产物 ``output_version`` 管理（enum / price / capital 目录编号）。

与 **工作台** ``version``（``sys_strategy_workbench_snapshot.version``）无关：
- ``output_version_id`` / ``output_version_dir``：本次 price 或 capital 运行产物目录；
- ``base_output_version_dir``：上游枚举 ``output_version`` 目录（price/capital 输入）。
"""

from datetime import datetime
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, FrozenSet, Literal, Optional, Set, Tuple

from core.infra.project_context import ProjectContext

logger = logging.getLogger(__name__)


_SimKind = Literal["enum", "price", "capital"]


def _read_next_output_version(meta: Dict[str, Any]) -> int:
    """``meta.json`` 下一磁盘 ``output_version`` 序号。"""
    try:
        return max(int(meta.get("next_output_version") or 1), 1)
    except (TypeError, ValueError):
        return 1


def _write_meta_after_create(meta: Dict[str, Any], created_id: int, **extra: Any) -> Dict[str, Any]:
    out = dict(meta or {})
    out.update(extra)
    out["next_output_version"] = int(created_id) + 1
    out["last_updated"] = datetime.now().isoformat()
    return out


def _numeric_version_dir_key(path: Path) -> int:
    """``latest`` 解析须按整型 id 比较，避免 ``\"9\" > \"20\"`` 的字典序陷阱。"""
    try:
        return int(path.name)
    except ValueError:
        return -1


def _pick_latest_numeric_version_dir(candidates: list[Path]) -> Path:
    if not candidates:
        raise ValueError("no version directories")
    return max(candidates, key=_numeric_version_dir_key)


class StrategyOutputVersionService:
    @staticmethod
    def create_enumerator_version(strategy_name: str) -> Tuple[Path, int]:
        root = ProjectContext.get_strategy_directory_simulation_enum(strategy_name)
        root.mkdir(parents=True, exist_ok=True)
        meta_path = root / "meta.json"
        if meta_path.exists():
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
        else:
            meta = {}

        output_version_id = _read_next_output_version(meta)
        version_dir = root / str(output_version_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        new_meta = _write_meta_after_create(meta, output_version_id, strategy_name=strategy_name)
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(new_meta, f, indent=2, ensure_ascii=False)
        return version_dir, output_version_id

    @staticmethod
    def resolve_enumerator_version(
        strategy_name: str,
        version_spec: str,
    ) -> Tuple[Path, Path]:
        root = ProjectContext.get_strategy_directory_simulation_enum(strategy_name)
        version_str = (version_spec or "latest").strip()
        if "/" in version_str:
            version_str = version_str.rsplit("/", 1)[-1].strip() or "latest"
        if not root.exists():
            raise FileNotFoundError(f"[StrategyOutputVersionService] enum dir missing: {root}")
        if version_str == "latest":
            candidates = [
                p for p in root.iterdir() if p.is_dir() and p.name[0].isdigit()
            ]
            if not candidates:
                raise FileNotFoundError(
                    f"[StrategyOutputVersionService] no versions under enum root: {root}"
                )
            return _pick_latest_numeric_version_dir(candidates), root
        version_dir = root / version_str
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(
                f"[StrategyOutputVersionService] version dir missing: {version_dir}"
            )
        return version_dir, root

    @staticmethod
    def create_price_factor_version(strategy_name: str) -> Tuple[Path, int]:
        root_dir = ProjectContext.get_strategy_directory_simulation_price(strategy_name)
        root_dir.mkdir(parents=True, exist_ok=True)
        meta_path = root_dir / "meta.json"
        if meta_path.exists():
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
        else:
            meta = {}
        output_version_id = _read_next_output_version(meta)
        version_dir = root_dir / str(output_version_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(
                _write_meta_after_create(meta, output_version_id, strategy_name=strategy_name),
                f,
                indent=2,
                ensure_ascii=False,
            )
        return version_dir, output_version_id

    @staticmethod
    def resolve_price_factor_version(
        strategy_name: str,
        version_spec: str,
    ) -> Tuple[Path, int]:
        root_dir = ProjectContext.get_strategy_directory_simulation_price(strategy_name)
        if not root_dir.exists():
            raise FileNotFoundError(
                f"[StrategyOutputVersionService] price factor simulator dir missing: {root_dir}"
            )
        if version_spec == "latest":
            candidates = [
                p for p in root_dir.iterdir() if p.is_dir() and p.name[0].isdigit()
            ]
            if not candidates:
                raise FileNotFoundError(
                    f"[StrategyOutputVersionService] no price factor versions: {root_dir}"
                )
            version_dir = _pick_latest_numeric_version_dir(candidates)
            return version_dir, int(version_dir.name)
        version_dir = root_dir / version_spec
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(
                f"[StrategyOutputVersionService] specified price factor version missing: {version_dir}"
            )
        return version_dir, int(version_spec)

    @staticmethod
    def create_capital_allocation_version(strategy_name: str) -> Tuple[Path, int]:
        base_dir = ProjectContext.get_strategy_directory_simulation_capital(strategy_name)
        base_dir.mkdir(parents=True, exist_ok=True)
        meta_file = base_dir / "meta.json"
        meta: Dict[str, Any] = {}
        if meta_file.exists():
            try:
                with meta_file.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
            except (json.JSONDecodeError, KeyError, ValueError):
                meta = {}
        output_version_id = _read_next_output_version(meta)
        version_dir = base_dir / str(output_version_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        with meta_file.open("w", encoding="utf-8") as f:
            json.dump(
                _write_meta_after_create(
                    meta,
                    output_version_id,
                    last_created_version=str(output_version_id),
                    last_created_at=datetime.now().isoformat(),
                ),
                f,
                indent=2,
                ensure_ascii=False,
            )
        return version_dir, output_version_id

    @staticmethod
    def resolve_capital_allocation_version(
        strategy_name: str,
        version_spec: str,
    ) -> Tuple[Path, int]:
        base_dir = ProjectContext.get_strategy_directory_simulation_capital(strategy_name)
        if not base_dir.exists():
            raise FileNotFoundError(
                f"[StrategyOutputVersionService] capital allocation simulator dir missing: {base_dir}"
            )
        if version_spec == "latest":
            version_dirs = [
                d for d in base_dir.iterdir() if d.is_dir() and d.name[0].isdigit()
            ]
            if not version_dirs:
                raise FileNotFoundError(
                    f"[StrategyOutputVersionService] no capital allocation versions: {base_dir}"
                )
            version_dir = _pick_latest_numeric_version_dir(version_dirs)
            return version_dir, int(version_dir.name)
        version_dir = base_dir / version_spec
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(
                f"[StrategyOutputVersionService] specified capital allocation version missing: {version_dir}"
            )
        return version_dir, int(version_spec)

    @staticmethod
    def resolve_output_version(
        strategy_name: str,
        output_version: str,
    ) -> Tuple[Path, Path]:
        version_dir, _ = StrategyOutputVersionService.resolve_enumerator_version(
            strategy_name, output_version
        )
        return version_dir, version_dir.parent

    @staticmethod
    def prune_simulation_versions(
        root_dir: Path,
        max_keep_versions: int,
        *,
        protected_dir_names: Optional[FrozenSet[str]] = None,
    ) -> Set[str]:
        """
        按版本目录名（数字 id）保留最新 ``max_keep_versions`` 个。

        ``protected_dir_names`` 中的目录名（如 ``"18"``）即使超出保留数也不删除；
        返回因保护而未删的目录名集合。
        """
        protected = frozenset(protected_dir_names or ())
        skipped: Set[str] = set()
        if max_keep_versions < 1 or not root_dir.is_dir():
            return skipped
        versions: list[tuple[int, Path]] = []
        for item in root_dir.iterdir():
            if not item.is_dir() or item.name in {"__pycache__"}:
                continue
            if not item.name.isdigit():
                continue
            try:
                version_id = int(item.name)
            except ValueError:
                continue
            versions.append((version_id, item))
        if len(versions) <= max_keep_versions:
            return skipped
        versions.sort(key=lambda x: x[0], reverse=True)
        for _, version_dir in versions[max_keep_versions:]:
            if version_dir.name in protected:
                skipped.add(version_dir.name)
                continue
            try:
                shutil.rmtree(version_dir)
                logger.info(
                    "pruned simulation output_version %s under %s (keep=%d)",
                    version_dir.name,
                    root_dir,
                    max_keep_versions,
                )
            except Exception as exc:
                logger.warning("prune failed for %s: %s", version_dir, exc)
        return skipped


__all__ = [
    "StrategyOutputVersionService",
]
