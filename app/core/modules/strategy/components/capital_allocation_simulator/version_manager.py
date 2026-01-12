#!/usr/bin/env python3
"""
CapitalAllocationSimulator 版本管理模块

负责管理模拟器结果目录的版本号，支持对同一个 SOT 进行多轮不同参数的回测对比。
"""

from pathlib import Path
from typing import Tuple
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CapitalAllocationSimulationVersionManager:
    """CapitalAllocationSimulator 版本管理器"""

    @staticmethod
    def create_simulation_version_dir(strategy_name: str) -> Tuple[Path, int]:
        """
        创建新的模拟器版本目录，并返回目录路径和版本号

        Args:
            strategy_name: 策略名称

        Returns:
            (version_dir, version_id): 版本目录路径和版本号
        """
        base_dir = Path(f"app/userspace/strategies/{strategy_name}/results/capital_allocation")
        base_dir.mkdir(parents=True, exist_ok=True)

        meta_file = base_dir / "meta.json"

        # 读取或创建 meta.json
        if meta_file.exists():
            try:
                with meta_file.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
                next_version_id = int(meta.get("next_version_id", 1))
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"[CapitalAllocationSimulationVersionManager] 读取 meta.json 失败: {e}，重置版本号")
                next_version_id = 1
        else:
            next_version_id = 1

        # 生成版本目录名：{version_id}_{timestamp}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_dir_name = f"{next_version_id}_{timestamp}"
        version_dir = base_dir / version_dir_name
        version_dir.mkdir(parents=True, exist_ok=True)

        # 更新 meta.json
        meta = {
            "next_version_id": next_version_id + 1,
            "last_created_version": version_dir_name,
            "last_created_at": datetime.now().isoformat(),
        }
        with meta_file.open("w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        logger.info(
            f"[CapitalAllocationSimulationVersionManager] 创建版本目录: {version_dir_name} (version_id={next_version_id})"
        )

        return version_dir, next_version_id

    @staticmethod
    def resolve_sot_version_dir(strategy_name: str, sot_version: str) -> Tuple[Path, Path]:
        """
        解析 SOT（枚举器）版本目录路径

        Args:
            strategy_name: 策略名称
            sot_version: SOT 版本标识
                - "latest": 使用最新的 SOT 版本（sot/ 目录）
                - "test/latest": 使用最新的测试版本（test/ 目录）
                - "1_20260112_161317": 使用指定版本号

        Returns:
            (sot_version_dir, enumerator_base_dir): SOT 版本目录路径和枚举器基础目录
        """
        enumerator_base_dir = Path(f"app/userspace/strategies/{strategy_name}/results/opportunity_enums")

        if sot_version == "latest":
            # 查找 sot/ 目录下最新的版本
            sot_dir = enumerator_base_dir / "sot"
            if not sot_dir.exists():
                raise ValueError(f"[CapitalAllocationSimulationVersionManager] SOT 目录不存在: {sot_dir}")
            
            version_dirs = [d for d in sot_dir.iterdir() if d.is_dir() and d.name[0].isdigit()]
            if not version_dirs:
                raise ValueError(f"[CapitalAllocationSimulationVersionManager] SOT 目录下没有找到任何版本: {sot_dir}")
            
            # 按版本号排序（假设目录名格式为 {version_id}_{timestamp}）
            version_dirs.sort(key=lambda d: d.name, reverse=True)
            sot_version_dir = version_dirs[0]
            
        elif sot_version == "test/latest":
            # 查找 test/ 目录下最新的版本
            test_dir = enumerator_base_dir / "test"
            if not test_dir.exists():
                raise ValueError(f"[CapitalAllocationSimulationVersionManager] test 目录不存在: {test_dir}")
            
            version_dirs = [d for d in test_dir.iterdir() if d.is_dir() and d.name[0].isdigit()]
            if not version_dirs:
                raise ValueError(f"[CapitalAllocationSimulationVersionManager] test 目录下没有找到任何版本: {test_dir}")
            
            version_dirs.sort(key=lambda d: d.name, reverse=True)
            sot_version_dir = version_dirs[0]
            
        elif sot_version.startswith("sot/"):
            # 显式指定 sot/ 下的版本
            version_id = sot_version[4:]  # 去掉 "sot/" 前缀
            sot_version_dir = enumerator_base_dir / "sot" / version_id
            if not sot_version_dir.exists():
                raise ValueError(f"[CapitalAllocationSimulationVersionManager] 指定的 SOT 版本目录不存在: {sot_version_dir}")
                
        else:
            # 假设是具体的版本号，先尝试 sot/，再尝试 test/
            sot_version_dir = enumerator_base_dir / "sot" / sot_version
            if not sot_version_dir.exists():
                test_version_dir = enumerator_base_dir / "test" / sot_version
                if test_version_dir.exists():
                    sot_version_dir = test_version_dir
                else:
                    raise ValueError(
                        f"[CapitalAllocationSimulationVersionManager] 指定的版本目录不存在: "
                        f"sot/{sot_version} 或 test/{sot_version}"
                    )

        logger.info(
            f"[CapitalAllocationSimulationVersionManager] 解析 SOT 版本: {sot_version} -> {sot_version_dir}"
        )

        return sot_version_dir, enumerator_base_dir
