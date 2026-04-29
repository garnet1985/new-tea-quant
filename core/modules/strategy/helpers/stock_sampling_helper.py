#!/usr/bin/env python3
"""Stock Sampling Helper - 股票采样助手。"""

import logging
from typing import Any, Dict, List, Optional

from core.infra.project_context.path_manager import PathManager

logger = logging.getLogger(__name__)


class StockSamplingHelper:
    @staticmethod
    def get_stock_list(
        all_stocks: List[Dict[str, Any]],
        sampling_amount: int,
        sampling_config: Dict[str, Any],
        strategy_name: Optional[str] = None,
    ) -> List[str]:
        all_stock_ids = [s["id"] for s in all_stocks]
        sampling_strategy = sampling_config.get("strategy", "uniform")
        if sampling_strategy == "uniform":
            return StockSamplingHelper.sample_uniform(all_stock_ids, sampling_amount)
        if sampling_strategy == "stratified":
            seed = sampling_config.get("stratified", {}).get("seed")
            return StockSamplingHelper.sample_stratified(all_stocks, sampling_amount, seed)
        if sampling_strategy == "random":
            seed = sampling_config.get("random", {}).get("seed")
            return StockSamplingHelper.sample_random(all_stock_ids, sampling_amount, seed)
        if sampling_strategy == "continuous":
            start_idx = sampling_config.get("continuous", {}).get("start_idx", 0)
            return StockSamplingHelper.sample_continuous(
                all_stock_ids, sampling_amount, start_idx
            )
        if sampling_strategy == "pool":
            pool_config = sampling_config.get("pool", {})
            stock_ids = pool_config.get("stock_ids", [])
            if not stock_ids:
                stock_ids = StockSamplingHelper._load_stock_ids_from_file(
                    strategy_name=strategy_name,
                    relative_file_path=pool_config.get("file"),
                    field_name="sampling.pool.file",
                )
            return StockSamplingHelper.sample_pool(stock_ids, sampling_amount)
        if sampling_strategy == "blacklist":
            blacklist_config = sampling_config.get("blacklist", {})
            blacklist_ids = blacklist_config.get("stock_ids", [])
            if not blacklist_ids:
                blacklist_ids = StockSamplingHelper._load_stock_ids_from_file(
                    strategy_name=strategy_name,
                    relative_file_path=blacklist_config.get("file"),
                    field_name="sampling.blacklist.file",
                )
            return StockSamplingHelper.sample_blacklist(
                all_stock_ids, blacklist_ids, sampling_amount
            )
        logger.warning("未知的采样策略: %s，使用全部股票", sampling_strategy)
        return all_stock_ids[:sampling_amount]

    @staticmethod
    def filter_stocks_by_list(
        all_stocks: List[Dict[str, Any]],
        watch_list: Any,
        strategy_name: Optional[str] = None,
    ) -> List[str]:
        if not watch_list:
            return [s["id"] for s in all_stocks]
        if isinstance(watch_list, list):
            wanted = {str(x).strip() for x in watch_list if str(x).strip()}
        else:
            wanted = set(
                StockSamplingHelper._load_stock_ids_from_file(
                    strategy_name=strategy_name,
                    relative_file_path=str(watch_list).strip(),
                    field_name="scanner.watch_list",
                )
            )
        return [s["id"] for s in all_stocks if s.get("id") in wanted]

    @staticmethod
    def sample_uniform(stock_ids: List[str], amount: int) -> List[str]:
        if amount >= len(stock_ids):
            return stock_ids
        step = len(stock_ids) // amount
        return [stock_ids[i * step] for i in range(amount)]

    @staticmethod
    def sample_stratified(stocks: List[Dict], amount: int, seed: int = None) -> List[str]:
        import random

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
        import random

        if seed is not None:
            random.seed(seed)
        return random.sample(stock_ids, min(amount, len(stock_ids)))

    @staticmethod
    def sample_continuous(stock_ids: List[str], amount: int, start_idx: int) -> List[str]:
        end_idx = min(start_idx + amount, len(stock_ids))
        return stock_ids[start_idx:end_idx]

    @staticmethod
    def sample_pool(stock_ids: List[str], amount: int) -> List[str]:
        return stock_ids[:amount]

    @staticmethod
    def sample_blacklist(
        stock_ids: List[str], blacklist_ids: List[str], amount: int
    ) -> List[str]:
        filtered = [sid for sid in stock_ids if sid not in blacklist_ids]
        return filtered[:amount]

    @staticmethod
    def _load_stock_ids_from_file(
        strategy_name: Optional[str],
        relative_file_path: Any,
        field_name: str,
    ) -> List[str]:
        if not strategy_name:
            logger.warning("[%s] 未提供 strategy_name，无法从文件读取股票列表", field_name)
            return []
        if not isinstance(relative_file_path, str) or not relative_file_path.strip():
            return []

        normalized = relative_file_path.strip()
        file_path = (PathManager.strategy(strategy_name) / normalized).resolve()
        try:
            file_path.relative_to(PathManager.strategy(strategy_name).resolve())
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

