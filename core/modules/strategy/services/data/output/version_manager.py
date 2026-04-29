#!/usr/bin/env python3
"""Output version manager for strategy artifacts."""

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Tuple

from core.infra.project_context import PathManager

logger = logging.getLogger(__name__)


class StrategyOutputVersionService:
    @staticmethod
    def create_enumerator_version(
        strategy_name: str,
        use_sampling: bool = False,
    ) -> Tuple[Path, int]:
        sub_dir_name = "test" if use_sampling else "output"
        sub_dir = PathManager.strategy_opportunity_enums(strategy_name, use_sampling)
        sub_dir.mkdir(parents=True, exist_ok=True)
        meta_path = sub_dir / "meta.json"
        if meta_path.exists():
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
        else:
            meta = {}

        next_version_id = int(meta.get("next_version_id", 1))
        version_dir = sub_dir / str(next_version_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        new_meta = {
            "next_version_id": next_version_id + 1,
            "last_updated": datetime.now().isoformat(),
            "strategy_name": strategy_name,
            "mode": sub_dir_name,
        }
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(new_meta, f, indent=2, ensure_ascii=False)
        return version_dir, next_version_id

    @staticmethod
    def resolve_enumerator_version(
        strategy_name: str,
        version_spec: str,
    ) -> Tuple[Path, Path]:
        if "/" in version_spec:
            sub_dir_name, version_str = version_spec.split("/", 1)
        else:
            sub_dir_name, version_str = "output", version_spec

        root = PathManager.strategy_opportunity_enums(
            strategy_name, use_sampling=(sub_dir_name == "test")
        )
        base_root = root.parent
        if not root.exists():
            raise FileNotFoundError(f"[StrategyOutputVersionService] enum dir missing: {root}")
        if version_str == "latest":
            candidates = [
                p for p in root.iterdir() if p.is_dir() and p.name[0].isdigit()
            ]
            if not candidates:
                raise FileNotFoundError(
                    f"[StrategyOutputVersionService] no versions under {sub_dir_name}: {root}"
                )
            return sorted(candidates, key=lambda p: p.name)[-1], base_root
        version_dir = root / version_str
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(f"[StrategyOutputVersionService] version dir missing: {version_dir}")
        return version_dir, base_root

    @staticmethod
    def create_price_factor_version(strategy_name: str) -> Tuple[Path, int]:
        root_dir = PathManager.strategy_simulations_price_factor(strategy_name)
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
        next_version_id = int(meta.get("next_version_id", 1))
        version_dir = root_dir / str(next_version_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "next_version_id": next_version_id + 1,
                    "last_updated": datetime.now().isoformat(),
                    "strategy_name": strategy_name,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        return version_dir, next_version_id

    @staticmethod
    def resolve_price_factor_version(
        strategy_name: str,
        version_spec: str,
    ) -> Tuple[Path, int]:
        root_dir = PathManager.strategy_simulations_price_factor(strategy_name)
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
            version_dir = sorted(candidates, key=lambda p: p.name)[-1]
            return version_dir, int(version_dir.name)
        version_dir = root_dir / version_spec
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(
                f"[StrategyOutputVersionService] specified price factor version missing: {version_dir}"
            )
        return version_dir, int(version_spec)

    @staticmethod
    def create_capital_allocation_version(strategy_name: str) -> Tuple[Path, int]:
        base_dir = PathManager.strategy_capital_allocation(strategy_name)
        base_dir.mkdir(parents=True, exist_ok=True)
        meta_file = base_dir / "meta.json"
        next_version_id = 1
        if meta_file.exists():
            try:
                with meta_file.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
                next_version_id = int(meta.get("next_version_id", 1))
            except (json.JSONDecodeError, KeyError, ValueError):
                next_version_id = 1
        version_dir = base_dir / str(next_version_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        with meta_file.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "next_version_id": next_version_id + 1,
                    "last_created_version": str(next_version_id),
                    "last_created_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        return version_dir, next_version_id

    @staticmethod
    def resolve_capital_allocation_version(
        strategy_name: str,
        version_spec: str,
    ) -> Tuple[Path, int]:
        base_dir = PathManager.strategy_capital_allocation(strategy_name)
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
            version_dirs.sort(key=lambda d: d.name, reverse=True)
            return version_dirs[0], int(version_dirs[0].name)
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
    def prune_enumerator_versions(root_dir: Path, max_keep_versions: int) -> None:
        if max_keep_versions < 1:
            return
        version_dirs = [
            item
            for item in root_dir.iterdir()
            if item.is_dir() and item.name != "__pycache__" and item.name[0].isdigit()
        ]
        versions = []
        for version_dir in version_dirs:
            metadata_path = version_dir / "0_metadata.json"
            if not metadata_path.exists():
                try:
                    version_id = int(version_dir.name)
                except ValueError:
                    continue
            else:
                try:
                    with metadata_path.open("r", encoding="utf-8") as f:
                        version_id = int((json.load(f) or {}).get("version_id", 0))
                except Exception:
                    continue
            versions.append((version_id, version_dir))
        versions.sort(key=lambda x: x[0], reverse=True)
        for _, version_dir in versions[max_keep_versions:]:
            try:
                import shutil

                shutil.rmtree(version_dir)
            except Exception as exc:
                logger.warning("prune failed for %s: %s", version_dir, exc)


__all__ = ["StrategyOutputVersionService"]
