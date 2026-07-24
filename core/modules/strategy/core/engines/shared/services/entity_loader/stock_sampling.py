"""股票采样（EnumeratorPipeline 层消费）。

本文件:
- StockSampler: uniform / stratified / random / pool / blacklist 等采样策略
  边界: 负责从 stock_list 得到 entity_ids；不负责 global 加载或 job 构建
"""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional

from core.infra.project_context import ProjectContext

logger = logging.getLogger(__name__)


class StockSampler:
    """股票采样器（采样策略）。"""

    @staticmethod
    def sample(
        stock_list: List[str],
        sampling_config: Dict[str, Any],
        strategy_name: Optional[str] = None,
    ) -> List[str]:
        """根据采样配置获取股票列表。

        Args:
            stock_list: 全量股票ID列表
            sampling_config: 采样配置（包含 strategy 和子配置）
            strategy_name: 策略名称（用于读取 pool/blacklist 文件）

        Returns:
            采样后的股票ID列表

        采样策略：
        - uniform：均匀采样（固定间隔）
        - stratified：分层采样（按市场分层）
        - random：随机采样（可设置 seed）
        - weighted：加权无放回（``weighted.weights`` / ``weighted.seed``）
        - continuous：连续采样（从 start_idx 开始）
        - pool：从指定 pool 采样（文件或直接配置 stock_ids）
        - blacklist：排除 blacklist 采样（文件或直接配置 blacklist_ids）
        """
        sampling_strategy = sampling_config.get("strategy", "uniform")
        
        if sampling_strategy == "uniform":
            return StockSampler._sample_uniformly(stock_list, sampling_config)

        if sampling_strategy == "stratified":
            return StockSampler._sample_stratified(stock_list, sampling_config)

        if sampling_strategy == "random":
            return StockSampler._sample_randomly(stock_list, sampling_config)

        if sampling_strategy == "weighted":
            return StockSampler._sample_weighted(stock_list, sampling_config)

        if sampling_strategy == "continuous":
            # 连续采样需要额外的 start_idx 参数
            start_idx = sampling_config.get("continuous", {}).get("start_idx", 0)
            amount = sampling_config.get("sampling_amount", 10)
            end_idx = min(start_idx + amount, len(stock_list))
            return stock_list[start_idx:end_idx]

        if sampling_strategy == "pool":
            return StockSampler._sample_from_white_list(stock_list, sampling_config, strategy_name)

        if sampling_strategy == "blacklist":
            return StockSampler._sample_exclude_black_list(stock_list, sampling_config, strategy_name)

        logger.warning("未知的采样策略: %s，使用全部股票", sampling_strategy)
        amount = sampling_config.get("sampling_amount", 10)
        return stock_list[:amount]

    @staticmethod
    def _sample_randomly(
        stock_list: List[str],
        sampling_config: Dict[str, Any],
    ) -> List[str]:
        """随机采样（可设置 seed）。"""
        seed = sampling_config.get("random", {}).get("seed")
        amount = sampling_config.get("sampling_amount", 10)
        
        if seed is not None:
            random.seed(seed)
        
        return random.sample(stock_list, min(amount, len(stock_list)))

    @staticmethod
    def _sample_uniformly(
        stock_list: List[str],
        sampling_config: Dict[str, Any],
    ) -> List[str]:
        """均匀采样（固定间隔）。"""
        amount = sampling_config.get("sampling_amount", 10)
        
        if amount >= len(stock_list):
            return stock_list
        
        step = len(stock_list) // amount
        return [stock_list[i * step] for i in range(amount)]

    @staticmethod
    def _sample_weighted(
        stock_list: List[str],
        sampling_config: Dict[str, Any],
    ) -> List[str]:
        """加权无放回采样。

        配置 ``sampling.weighted``:
        - ``weights``: ``{stock_id: weight}``，缺省权重 1.0
        - ``seed``: 可选随机种子
        """
        amount = int(sampling_config.get("sampling_amount", 10) or 10)
        if amount <= 0 or not stock_list:
            return []
        if amount >= len(stock_list):
            return list(stock_list)

        cfg = sampling_config.get("weighted") or {}
        seed = cfg.get("seed")
        weights_map = cfg.get("weights") if isinstance(cfg.get("weights"), dict) else {}
        if seed is not None:
            random.seed(seed)

        remaining = list(stock_list)
        remaining_weights = [
            max(0.0, float(weights_map.get(sid, 1.0) or 0.0)) for sid in remaining
        ]
        if sum(remaining_weights) <= 0:
            logger.warning("weighted 权重全为 0，回退均匀采样")
            return StockSampler._sample_uniformly(stock_list, sampling_config)

        picked: List[str] = []
        for _ in range(amount):
            if not remaining:
                break
            total = sum(remaining_weights)
            if total <= 0:
                break
            choice = random.choices(remaining, weights=remaining_weights, k=1)[0]
            idx = remaining.index(choice)
            picked.append(choice)
            del remaining[idx]
            del remaining_weights[idx]
        return picked

    @staticmethod
    def _sample_stratified(
        stock_list: List[str],
        sampling_config: Dict[str, Any],
    ) -> List[str]:
        """分层采样（按市场分层：科创板、沪市主板、创业板、深市主板等）。

        注意：stock_list 是 ID 列表，需要额外的股票信息进行分层。
        如果只有 ID，无法准确分层，会退化到均匀采样。
        """
        seed = sampling_config.get("stratified", {}).get("seed")
        amount = sampling_config.get("sampling_amount", 10)
        
        # 简化实现：根据股票代码前缀进行粗略分层
        if seed is not None:
            random.seed(seed)
        
        # 按市场粗略分组（基于股票代码前缀）
        market_groups = {}
        for stock_id in stock_list:
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
        total_stocks = len(stock_list)
        for _market, ids in market_groups.items():
            market_ratio = len(ids) / total_stocks
            market_amount = max(1, int(amount * market_ratio))
            result.extend(random.sample(ids, min(market_amount, len(ids))))
        
        if len(result) < amount:
            remaining = [sid for sid in stock_list if sid not in result]
            result.extend(random.sample(remaining, min(amount - len(result), len(remaining))))
        
        return result[:amount]

    @staticmethod
    def _sample_from_white_list(
        stock_list: List[str],
        sampling_config: Dict[str, Any],
        strategy_name: Optional[str] = None,
    ) -> List[str]:
        """从白名单采样（pool 配置）。"""
        pool_config = sampling_config.get("pool", {})
        white_list = pool_config.get("stock_ids", [])
        
        # 如果没有直接配置 stock_ids，从文件读取
        if not white_list:
            white_list = StockSampler._load_stock_ids_from_file(
                strategy_name=strategy_name,
                relative_file_path=pool_config.get("file"),
                field_name="sampling.pool.file",
            )
        
        amount = sampling_config.get("sampling_amount", 10)
        return white_list[:amount]

    @staticmethod
    def _sample_exclude_black_list(
        stock_list: List[str],
        sampling_config: Dict[str, Any],
        strategy_name: Optional[str] = None,
    ) -> List[str]:
        """排除黑名单采样（blacklist 配置）。"""
        blacklist_config = sampling_config.get("blacklist", {})
        black_list = blacklist_config.get("stock_ids", [])
        
        # 如果没有直接配置 blacklist_ids，从文件读取
        if not black_list:
            black_list = StockSampler._load_stock_ids_from_file(
                strategy_name=strategy_name,
                relative_file_path=blacklist_config.get("file"),
                field_name="sampling.blacklist.file",
            )
        
        # 排除黑名单
        filtered = [sid for sid in stock_list if sid not in black_list]
        amount = sampling_config.get("sampling_amount", 10)
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


__all__ = ["StockSampler"]