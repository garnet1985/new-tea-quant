#!/usr/bin/env python3
"""股票采样解析辅助函数。"""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional

from core.infra.project_context import ProjectContext

logger = logging.getLogger(__name__)


class StockSamplingResolver:
    """股票采样解析器（采样策略）。"""

    @staticmethod
    def get_stock_list(
        all_stocks: List[Dict[str, Any]],
        sampling_amount: int,
        sampling_config: Dict[str, Any],
        strategy_name: Optional[str] = None,
    ) -> List[str]:
        """根据采样配置获取股票列表。

        Args:
            all_stocks: 全量股票列表（包含 id、name 等字段）
            sampling_amount: 采样数量
            sampling_config: 采样配置（包含 strategy 和子配置）
            strategy_name: 策略名称（用于读取 pool/blacklist 文件）

        Returns:
            采样后的股票ID列表

        采样策略：
        - uniform：均匀采样（固定间隔）
        - stratified：分层采样（按市场分层）
        - random：随机采样（可设置 seed）
        - continuous：连续采样（从 start_idx 开始）
        - pool：从指定 pool 采样（文件或直接配置 stock_ids）
        - blacklist：排除 blacklist 采样（文件或直接配置 blacklist_ids）
        """
        all_stock_ids = [s["id"] for s in all_stocks]
        sampling_strategy = sampling_config.get("strategy", "uniform")
        
        if sampling_strategy == "uniform":
            return StockSamplingResolver.sample_uniform(all_stock_ids, sampling_amount)
        
        if sampling_strategy == "stratified":
            seed = sampling_config.get("stratified", {}).get("seed")
            return StockSamplingResolver.sample_stratified(all_stocks, sampling_amount, seed)
        
        if sampling_strategy == "random":
            seed = sampling_config.get("random", {}).get("seed")
            return StockSamplingResolver.sample_random(all_stock_ids, sampling_amount, seed)
        
        if sampling_strategy == "continuous":
            start_idx = sampling_config.get("continuous", {}).get("start_idx", 0)
            return StockSamplingResolver.sample_continuous(
                all_stock_ids, sampling_amount, start_idx
            )
        
        if sampling_strategy == "pool":
            pool_config = sampling_config.get("pool", {})
            stock_ids = pool_config.get("stock_ids", [])
            if not stock_ids:
                stock_ids = StockSamplingResolver._load_stock_ids_from_file(
                    strategy_name=strategy_name,
                    relative_file_path=pool_config.get("file"),
                    field_name="sampling.pool.file",
                )
            return StockSamplingResolver.sample_pool(stock_ids, sampling_amount)
        
        if sampling_strategy == "blacklist":
            blacklist_config = sampling_config.get("blacklist", {})
            blacklist_ids = blacklist_config.get("stock_ids", [])
            if not blacklist_ids:
                blacklist_ids = StockSamplingResolver._load_stock_ids_from_file(
                    strategy_name=strategy_name,
                    relative_file_path=blacklist_config.get("file"),
                    field_name="sampling.blacklist.file",
                )
            return StockSamplingResolver.sample_blacklist(
                all_stock_ids, blacklist_ids, sampling_amount
            )
        
        logger.warning("未知的采样策略: %s，使用全部股票", sampling_strategy)
        return all_stock_ids[:sampling_amount]

    @staticmethod
    def sample_uniform(stock_ids: List[str], amount: int) -> List[str]:
        """均匀采样（固定间隔）。"""
        if amount >= len(stock_ids):
            return stock_ids
        step = len(stock_ids) // amount
        return [stock_ids[i * step] for i in range(amount)]

    @staticmethod
    def sample_stratified(stocks: List[Dict], amount: int, seed: int = None) -> List[str]:
        """分层采样（按市场分层：科创板、沪市主板、创业板、深市主板等）。"""
        if seed is not None:
            random.seed(seed)
        
        market_groups = {}
        for stock in stocks:
            stock_id = stock["id"]
            if stock_id.endswith(".SH"):
                if stock_id.startswith("688"):
                    market = "科创板"
                elif stock_id.startswith("60"):
                    market = "沪市主板"
                else:
                    market = "其他沪市"
            elif stock_id.endswith(".SZ"):
                if stock_id.startswith("300"):
                    market = "创业板"
                elif stock_id.startswith("002"):
                    market = "中小板"
                elif stock_id.startswith("000"):
                    market = "深市主板"
                else:
                    market = "其他深市"
            else:
                market = "其他"
            market_groups.setdefault(market, []).append(stock_id)

        result = []
        total_stocks = len(stocks)
        for _market, ids in market_groups.items():
            market_ratio = len(ids) / total_stocks
            market_amount = max(1, int(amount * market_ratio))
            result.extend(random.sample(ids, min(market_amount, len(ids))))
        
        if len(result) < amount:
            all_ids = [s["id"] for s in stocks]
            remaining = [sid for sid in all_ids if sid not in result]
            result.extend(random.sample(remaining, min(amount - len(result), len(remaining))))
        
        return result[:amount]

    @staticmethod
    def sample_random(stock_ids: List[str], amount: int, seed: int = None) -> List[str]:
        """随机采样（可设置 seed）。"""
        if seed is not None:
            random.seed(seed)
        return random.sample(stock_ids, min(amount, len(stock_ids)))

    @staticmethod
    def sample_continuous(stock_ids: List[str], amount: int, start_idx: int) -> List[str]:
        """连续采样（从 start_idx 开始）。"""
        end_idx = min(start_idx + amount, len(stock_ids))
        return stock_ids[start_idx:end_idx]

    @staticmethod
    def sample_pool(stock_ids: List[str], amount: int) -> List[str]:
        """从指定 pool 采样。"""
        return stock_ids[:amount]

    @staticmethod
    def sample_blacklist(
        stock_ids: List[str], blacklist_ids: List[str], amount: int
    ) -> List[str]:
        """排除 blacklist 采样。"""
        filtered = [sid for sid in stock_ids if sid not in blacklist_ids]
        return filtered[:amount]

    @staticmethod
    def _load_stock_ids_from_file(
        strategy_name: Optional[str],
        relative_file_path: Any,
        field_name: str,
    ) -> List[str]:
        """从文件加载股票ID列表。

        Args:
            strategy_name: 策略名称（用于定位文件路径）
            relative_file_path: 相对文件路径（相对于策略目录）
            field_name: 字段名称（用于日志）

        Returns:
            股票ID列表

        文件格式：
        - 每行一个股票代码
        - 支持 # 注释
        - 自动去除重复和空行
        """
        if not strategy_name:
            logger.warning("[%s] 未提供 strategy_name，无法从文件读取股票列表", field_name)
            return []
        
        if not isinstance(relative_file_path, str) or not relative_file_path.strip():
            return []

        normalized = relative_file_path.strip()
        strategy_dir = ProjectContext.path.get_strategy_directory(strategy_name).resolve()
        file_path = (strategy_dir / normalized).resolve()
        
        # 验证路径不越界
        try:
            file_path.relative_to(strategy_dir)
        except ValueError:
            logger.warning("[%s] 路径越界，已拒绝: %s", field_name, normalized)
            return []
        
        if not file_path.exists() or not file_path.is_file():
            logger.warning("[%s] 文件不存在: %s", field_name, file_path)
            return []

        stock_ids: List[str] = []
        seen = set()
        try:
            with file_path.open("r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    value = line.split("#", 1)[0].strip()
                    if not value or value in seen:
                        continue
                    seen.add(value)
                    stock_ids.append(value)
        except Exception as e:
            logger.warning("[%s] 读取失败: %s, error=%s", field_name, file_path, e)
            return []

        if stock_ids:
            logger.info("[%s] 从文件加载股票数量: %d (%s)", field_name, len(stock_ids), file_path)
        else:
            logger.warning("[%s] 文件为空或无有效股票代码: %s", field_name, file_path)
        
        return stock_ids


__all__ = ["StockSamplingResolver"]