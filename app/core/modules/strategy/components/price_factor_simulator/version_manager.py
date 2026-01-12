#!/usr/bin/env python3
"""
版本管理模块

负责：
- 创建模拟器版本目录
- 解析 SOT 版本目录
"""

from pathlib import Path
from typing import Tuple
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class SimulationVersionManager:
    """模拟器版本管理器"""

    @staticmethod
    def create_simulation_version_dir(strategy_name: str) -> Tuple[Path, int]:
        """
        创建模拟器版本目录（使用自己的版本管理，类似枚举器）。
        
        目录结构：
            app/userspace/strategies/{strategy}/results/simulations/price_factor/
                meta.json  # 版本管理元信息
                {version_id}_{YYYYMMDD_HHMMSS}/  # 模拟器版本目录
        
        Returns:
            (version_dir, version_id): 版本目录路径和版本ID
        """
        root_dir = (
            Path("app")
            / "userspace"
            / "strategies"
            / strategy_name
            / "results"
            / "simulations"
            / "price_factor"
        )
        root_dir.mkdir(parents=True, exist_ok=True)

        # 读取或创建 meta.json
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
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        version_dir_name = f"{next_version_id}_{timestamp_str}"
        version_dir = root_dir / version_dir_name
        version_dir.mkdir(parents=True, exist_ok=True)

        # 立刻更新 meta.json（版本管理），不依赖后续流程是否成功
        new_meta = {
            "next_version_id": next_version_id + 1,
            "last_updated": now.isoformat(),
            "strategy_name": strategy_name,
        }
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(new_meta, f, indent=2, ensure_ascii=False)

        return version_dir, next_version_id

    @staticmethod
    def resolve_sot_version_dir(strategy_name: str, sot_version: str) -> Tuple[Path, Path]:
        """
        解析枚举版本目录：
        
        支持的格式：
        - "latest": 使用最新的 SOT 版本（sot/ 目录）
        - "test/latest": 使用最新的测试版本（test/ 目录）
        - "sot/latest": 使用最新的 SOT 版本（sot/ 目录）
        - "1_20260112_161317": 使用指定版本号（默认在 sot/ 目录查找）
        - "test/1_20260112_161317": 使用指定测试版本号（test/ 目录）
        - "sot/1_20260112_161317": 使用指定 SOT 版本号（sot/ 目录）
        """
        base_root = (
            Path("app")
            / "userspace"
            / "strategies"
            / strategy_name
            / "results"
            / "opportunity_enums"
        )

        # 解析目录类型和版本号
        if "/" in sot_version:
            # 格式：test/latest 或 sot/latest 或 test/1_xxx 或 sot/1_xxx
            parts = sot_version.split("/", 1)
            sub_dir_name = parts[0]  # test 或 sot
            version_str = parts[1]  # latest 或具体版本号
        else:
            # 格式：latest 或 1_xxx（默认使用 sot 目录）
            sub_dir_name = "sot"
            version_str = sot_version

        root = base_root / sub_dir_name
        if not root.exists():
            raise FileNotFoundError(
                f"[PriceFactorSimulator] 枚举目录不存在: {root} (sot_version={sot_version})"
            )

        if version_str == "latest":
            # 查找最新的版本目录
            candidates = [p for p in root.iterdir() if p.is_dir() and "_" in p.name]
            if not candidates:
                raise FileNotFoundError(
                    f"[PriceFactorSimulator] {sub_dir_name} 目录下没有任何版本: {root}"
                )
            # 版本名形如: {version_id}_{YYYYMMDD_HHMMSS}，直接按 name 排序即可
            version_dir = sorted(candidates, key=lambda p: p.name)[-1]
            logger.info(
                f"[PriceFactorSimulator] 使用最新版本: {sub_dir_name}/{version_dir.name}"
            )
            return root, version_dir

        # 使用指定版本号
        version_dir = root / version_str
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(
                f"[PriceFactorSimulator] 指定版本目录不存在: {version_dir} (sot_version={sot_version})"
            )
        logger.info(
            f"[PriceFactorSimulator] 使用指定版本: {sub_dir_name}/{version_str}"
        )
        return root, version_dir
