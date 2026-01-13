#!/usr/bin/env python3
"""
Version Manager - 统一版本管理器

职责：
- 统一管理所有组件的版本目录创建和解析
- 支持枚举器、价格因子模拟器、资金分配模拟器的版本管理
- 提供统一的 SOT 版本解析接口

设计原则：
- 使用静态方法（无状态，高效）
- 统一的版本目录命名格式：{version_id}_{YYYYMMDD_HHMMSS}
- 统一的 meta.json 管理
"""

from pathlib import Path
from typing import Tuple, Literal
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class VersionManager:
    """统一版本管理器（静态方法）"""
    
    # =========================================================================
    # 枚举器版本管理
    # =========================================================================
    
    @staticmethod
    def create_enumerator_version(
        strategy_name: str,
        use_sampling: bool = False
    ) -> Tuple[Path, int]:
        """
        创建枚举器版本目录
        
        目录结构：
            app/userspace/strategies/{strategy}/results/opportunity_enums/
                {test|sot}/
                    meta.json  # 版本管理元信息
                    {version_id}_{YYYYMMDD_HHMMSS}/  # 版本目录
        
        Args:
            strategy_name: 策略名称
            use_sampling: 是否使用采样模式
                - True: 使用 test/ 子目录
                - False: 使用 sot/ 子目录
        
        Returns:
            (version_dir, version_id): 版本目录路径和版本ID
        """
        sub_dir_name = "test" if use_sampling else "sot"
        root_dir = (
            Path("app")
            / "userspace"
            / "strategies"
            / strategy_name
            / "results"
            / "opportunity_enums"
        )
        sub_dir = root_dir / sub_dir_name
        sub_dir.mkdir(parents=True, exist_ok=True)
        
        # 读取或创建 meta.json
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
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        version_dir_name = f"{next_version_id}_{timestamp_str}"
        version_dir = sub_dir / version_dir_name
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # 立刻更新 meta.json（版本管理），不依赖后续流程是否成功
        new_meta = {
            "next_version_id": next_version_id + 1,
            "last_updated": now.isoformat(),
            "strategy_name": strategy_name,
            "mode": sub_dir_name,  # 记录模式：test 或 sot
        }
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(new_meta, f, indent=2, ensure_ascii=False)
        
        logger.info(
            f"[VersionManager] 创建枚举器版本: {sub_dir_name}/{version_dir_name} "
            f"(version_id={next_version_id})"
        )
        
        return version_dir, next_version_id
    
    @staticmethod
    def resolve_enumerator_version(
        strategy_name: str,
        version_spec: str
    ) -> Tuple[Path, Path]:
        """
        解析枚举器版本目录
        
        支持的格式：
        - "latest": 使用最新的 SOT 版本（sot/ 目录）
        - "test/latest": 使用最新的测试版本（test/ 目录）
        - "sot/latest": 使用最新的 SOT 版本（sot/ 目录）
        - "1_20260112_161317": 使用指定版本号（默认在 sot/ 目录查找）
        - "test/1_20260112_161317": 使用指定测试版本号（test/ 目录）
        - "sot/1_20260112_161317": 使用指定 SOT 版本号（sot/ 目录）
        
        Args:
            strategy_name: 策略名称
            version_spec: 版本标识符
        
        Returns:
            (version_dir, base_dir): 版本目录路径和基础目录路径
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
        if "/" in version_spec:
            # 格式：test/latest 或 sot/latest 或 test/1_xxx 或 sot/1_xxx
            parts = version_spec.split("/", 1)
            sub_dir_name = parts[0]  # test 或 sot
            version_str = parts[1]  # latest 或具体版本号
        else:
            # 格式：latest 或 1_xxx（默认使用 sot 目录）
            sub_dir_name = "sot"
            version_str = version_spec
        
        root = base_root / sub_dir_name
        if not root.exists():
            raise FileNotFoundError(
                f"[VersionManager] 枚举目录不存在: {root} (version_spec={version_spec})"
            )
        
        if version_str == "latest":
            # 查找最新的版本目录
            candidates = [p for p in root.iterdir() if p.is_dir() and "_" in p.name]
            if not candidates:
                raise FileNotFoundError(
                    f"[VersionManager] {sub_dir_name} 目录下没有任何版本: {root}"
                )
            # 版本名形如: {version_id}_{YYYYMMDD_HHMMSS}，直接按 name 排序即可
            version_dir = sorted(candidates, key=lambda p: p.name)[-1]
            logger.info(
                f"[VersionManager] 使用最新枚举器版本: {sub_dir_name}/{version_dir.name}"
            )
            return version_dir, base_root
        
        # 使用指定版本号
        version_dir = root / version_str
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(
                f"[VersionManager] 指定版本目录不存在: {version_dir} (version_spec={version_spec})"
            )
        logger.info(
            f"[VersionManager] 使用指定枚举器版本: {sub_dir_name}/{version_str}"
        )
        return version_dir, base_root
    
    # =========================================================================
    # 价格因子模拟器版本管理
    # =========================================================================
    
    @staticmethod
    def create_price_factor_version(strategy_name: str) -> Tuple[Path, int]:
        """
        创建价格因子模拟器版本目录
        
        目录结构：
            app/userspace/strategies/{strategy}/results/simulations/price_factor/
                meta.json  # 版本管理元信息
                {version_id}_{YYYYMMDD_HHMMSS}/  # 模拟器版本目录
        
        Args:
            strategy_name: 策略名称
        
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
        
        logger.info(
            f"[VersionManager] 创建价格因子模拟器版本: {version_dir_name} "
            f"(version_id={next_version_id})"
        )
        
        return version_dir, next_version_id
    
    @staticmethod
    def resolve_price_factor_version(
        strategy_name: str,
        version_spec: str
    ) -> Tuple[Path, int]:
        """
        解析价格因子模拟器版本目录
        
        Args:
            strategy_name: 策略名称
            version_spec: 版本标识符（"latest" 或具体版本号）
        
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
        
        if not root_dir.exists():
            raise FileNotFoundError(
                f"[VersionManager] 价格因子模拟器目录不存在: {root_dir}"
            )
        
        if version_spec == "latest":
            # 查找最新的版本目录
            candidates = [p for p in root_dir.iterdir() if p.is_dir() and "_" in p.name]
            if not candidates:
                raise FileNotFoundError(
                    f"[VersionManager] 价格因子模拟器目录下没有任何版本: {root_dir}"
                )
            version_dir = sorted(candidates, key=lambda p: p.name)[-1]
            # 从目录名提取版本ID：{version_id}_{timestamp}
            version_id = int(version_dir.name.split("_")[0])
            logger.info(
                f"[VersionManager] 使用最新价格因子模拟器版本: {version_dir.name}"
            )
            return version_dir, version_id
        
        # 使用指定版本号
        version_dir = root_dir / version_spec
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(
                f"[VersionManager] 指定价格因子模拟器版本目录不存在: {version_dir}"
            )
        version_id = int(version_spec.split("_")[0])
        logger.info(
            f"[VersionManager] 使用指定价格因子模拟器版本: {version_spec}"
        )
        return version_dir, version_id
    
    # =========================================================================
    # 资金分配模拟器版本管理
    # =========================================================================
    
    @staticmethod
    def create_capital_allocation_version(strategy_name: str) -> Tuple[Path, int]:
        """
        创建资金分配模拟器版本目录
        
        目录结构：
            app/userspace/strategies/{strategy}/results/capital_allocation/
                meta.json  # 版本管理元信息
                {version_id}_{YYYYMMDD_HHMMSS}/  # 模拟器版本目录
        
        Args:
            strategy_name: 策略名称
        
        Returns:
            (version_dir, version_id): 版本目录路径和版本ID
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
                logger.warning(
                    f"[VersionManager] 读取 meta.json 失败: {e}，重置版本号"
                )
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
            f"[VersionManager] 创建资金分配模拟器版本: {version_dir_name} "
            f"(version_id={next_version_id})"
        )
        
        return version_dir, next_version_id
    
    @staticmethod
    def resolve_capital_allocation_version(
        strategy_name: str,
        version_spec: str
    ) -> Tuple[Path, int]:
        """
        解析资金分配模拟器版本目录
        
        Args:
            strategy_name: 策略名称
            version_spec: 版本标识符（"latest" 或具体版本号）
        
        Returns:
            (version_dir, version_id): 版本目录路径和版本ID
        """
        base_dir = Path(f"app/userspace/strategies/{strategy_name}/results/capital_allocation")
        
        if not base_dir.exists():
            raise FileNotFoundError(
                f"[VersionManager] 资金分配模拟器目录不存在: {base_dir}"
            )
        
        if version_spec == "latest":
            # 查找最新的版本目录
            version_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name[0].isdigit()]
            if not version_dirs:
                raise FileNotFoundError(
                    f"[VersionManager] 资金分配模拟器目录下没有任何版本: {base_dir}"
                )
            # 按版本号排序（假设目录名格式为 {version_id}_{timestamp}）
            version_dirs.sort(key=lambda d: d.name, reverse=True)
            version_dir = version_dirs[0]
            version_id = int(version_dir.name.split("_")[0])
            logger.info(
                f"[VersionManager] 使用最新资金分配模拟器版本: {version_dir.name}"
            )
            return version_dir, version_id
        
        # 使用指定版本号
        version_dir = base_dir / version_spec
        if not version_dir.exists() or not version_dir.is_dir():
            raise FileNotFoundError(
                f"[VersionManager] 指定资金分配模拟器版本目录不存在: {version_dir}"
            )
        version_id = int(version_spec.split("_")[0])
        logger.info(
            f"[VersionManager] 使用指定资金分配模拟器版本: {version_spec}"
        )
        return version_dir, version_id
    
    # =========================================================================
    # 通用 SOT 版本解析（向后兼容）
    # =========================================================================
    
    @staticmethod
    def resolve_sot_version(
        strategy_name: str,
        sot_version: str
    ) -> Tuple[Path, Path]:
        """
        解析 SOT（枚举器）版本目录（通用方法，向后兼容）
        
        这是 resolve_enumerator_version 的别名，用于向后兼容。
        建议新代码直接使用 resolve_enumerator_version。
        
        Args:
            strategy_name: 策略名称
            sot_version: SOT 版本标识符
        
        Returns:
            (version_dir, base_dir): 版本目录路径和基础目录路径
        """
        return VersionManager.resolve_enumerator_version(strategy_name, sot_version)
