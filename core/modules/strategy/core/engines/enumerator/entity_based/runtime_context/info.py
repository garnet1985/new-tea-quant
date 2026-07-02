"""entity_based 模式 general info。"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings
from core.modules.strategy.core.services.discovery.data.discovered_strategy import StrategyInfo

logger = logging.getLogger(__name__)

# ── 常量定义 ──
METADATA_FILE_NAME = "0_metadata.json"
VALID_EXECUTION_MODES = ["entity_based", "slice_based"]
DEFAULT_USERSPACE_ROOT = Path("userspace")


@dataclass
class EntityBasedGeneralInfo:
    """entity_based 回测全局信息（不可变）。"""

    # 核心标识
    strategy_id: str               # 策略ID（relative_path）
    key: str                       # settings.meta.key（全局唯一）

    # 回测范围
    start_date: str                # 回测开始日期
    end_date: str                  # 回测结束日期
    entity_ids: List[str]          # 回测entity列表

    # 执行模式
    execution_mode: str            # 执行模式（entity_based/slice_based）

    # 输出路径
    version_id: int                # 版本ID
    version_dir_name: str          # 版本目录名（如 "v1"）
    fingerprint_hash: str          # 指纹哈希（用于缓存查找）
    output_dir: Path               # 输出目录

    @classmethod
    def init(cls, strategy_info: StrategyInfo, settings_obj: StrategySettings) -> EntityBasedGeneralInfo:
        """初始化general info（计算version/output/params/fingerprint）。

        Args:
            strategy_info: 策略信息（基础信息）
            settings_obj: validated settings对象（验证过的settings）
        """

        # 1. 解析回测参数（从validated settings取值）
        start_date, end_date, entity_ids = cls._resolve_backtest_params(strategy_info, settings_obj)

        # 2. 计算fingerprint_hash（私有逻辑）
        fingerprint_hash = cls._compute_fingerprint_hash(strategy_info, start_date, end_date, entity_ids)

        # 3. 计算version/output_dir（私有逻辑）
        version_id, version_dir_name, output_dir = cls._resolve_output_paths(
            strategy_info.unique_relative_path,
            fingerprint_hash,
        )

        # 4. 获取execution_mode（从EnabledStrategyInfo的验证过的API获取）
        execution_mode = strategy_info.get_execution_mode()

        return cls(
            strategy_id=strategy_info.unique_relative_path,
            key=strategy_info.key,
            start_date=start_date,
            end_date=end_date,
            entity_ids=entity_ids,
            execution_mode=execution_mode,
            version_id=version_id,
            version_dir_name=version_dir_name,
            fingerprint_hash=fingerprint_hash,
            output_dir=output_dir,
        )

    # ── 私有逻辑方法 ──

    @staticmethod
    def _resolve_backtest_params(strategy_info: StrategyInfo, settings_obj: StrategySettings) -> tuple[str, str, List[str]]:
        """解析回测参数（从validated settings取值）。"""
        # 从validated settings取值（不需要再次validate）
        start_date = settings_obj.raw_settings["core"]["start_date"]
        end_date = settings_obj.raw_settings["core"]["end_date"]

        # 解析entity_ids（优先0_metadata.json，其次settings.sampling.stock_pool）
        entity_ids = cls._load_entity_ids(strategy_info)

        if not entity_ids:
            raise ValueError("No entity_ids found (0_metadata.json or settings.sampling.stock_pool)")

        return start_date, end_date, entity_ids

    @staticmethod
    def _load_entity_ids(strategy_info: StrategyInfo) -> List[str]:
        """加载entity_ids。"""
        metadata_file = strategy_info.folder / METADATA_FILE_NAME
        if metadata_file.is_file():
            try:
                with metadata_file.open("r", encoding="utf-8") as handle:
                    metadata = json.load(handle)
                entity_ids = metadata.get("stock_ids", [])
                if entity_ids:
                    logger.info("Loaded entity_ids from %s (%d stocks)", METADATA_FILE_NAME, len(entity_ids))
                    return entity_ids
            except Exception as exc:
                logger.warning("Failed to load entity_ids from %s: %s", METADATA_FILE_NAME, exc)

        # 从settings.sampling.stock_pool加载
        return strategy_info.settings.get("sampling", {}).get("stock_pool", [])

    @staticmethod
    def _compute_fingerprint_hash(
        strategy_info: StrategyInfo,
        start_date: str,
        end_date: str,
        entity_ids: List[str],
    ) -> str:
        """计算fingerprint_hash（简化版）。"""
        # TODO: 实现完整的fingerprint计算逻辑
        return f"{strategy_info.key}_{start_date}_{end_date}_{len(entity_ids)}"

    @staticmethod
    def _resolve_output_paths(strategy_id: str, fingerprint_hash: str) -> tuple[int, str, Path]:
        """计算version/output_dir（私有逻辑）。"""
        # 简化版version计算
        version_id = 1  # TODO: 从数据库查找相同fingerprint的version

        version_dir_name = f"v{version_id}"
        output_dir = DEFAULT_USERSPACE_ROOT / strategy_id / "versions" / version_dir_name

        logger.info("Resolved output paths: version_id=%d, output_dir=%s", version_id, output_dir)

        return version_id, version_dir_name, output_dir


__all__ = ["EntityBasedGeneralInfo"]