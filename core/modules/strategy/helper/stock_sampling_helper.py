#!/usr/bin/env python3
"""
Stock Sampling Helper - 股票采样助手

职责：
- 根据配置执行不同的采样策略
- 支持 6 种采样方式
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class StockSamplingHelper:
    """股票采样助手"""
    
    @staticmethod
    def get_stock_list(
        all_stocks: List[Dict[str, Any]], 
        sampling_amount: int,
        sampling_config: Dict[str, Any]
    ) -> List[str]:
        """
        获取股票列表（根据采样配置）
        
        Args:
            all_stocks: 全部股票列表 [{'id': '000001.SZ', ...}, ...]
            sampling_amount: 采样数量
            sampling_config: 采样配置
        
        Returns:
            stock_ids: 股票代码列表
        """
        all_stock_ids = [s['id'] for s in all_stocks]
        sampling_strategy = sampling_config.get('strategy', 'uniform')
        
        # 根据采样策略筛选
        if sampling_strategy == 'uniform':
            return StockSamplingHelper.sample_uniform(all_stock_ids, sampling_amount)
        
        elif sampling_strategy == 'stratified':
            seed = sampling_config.get('stratified', {}).get('seed')
            return StockSamplingHelper.sample_stratified(all_stocks, sampling_amount, seed)
        
        elif sampling_strategy == 'random':
            seed = sampling_config.get('random', {}).get('seed')
            return StockSamplingHelper.sample_random(all_stock_ids, sampling_amount, seed)
        
        elif sampling_strategy == 'continuous':
            start_idx = sampling_config.get('continuous', {}).get('start_idx', 0)
            return StockSamplingHelper.sample_continuous(all_stock_ids, sampling_amount, start_idx)
        
        elif sampling_strategy == 'pool':
            stock_pool = sampling_config.get('pool', {}).get('stock_pool', [])
            return StockSamplingHelper.sample_pool(stock_pool, sampling_amount)
        
        elif sampling_strategy == 'blacklist':
            blacklist = sampling_config.get('blacklist', {}).get('blacklist', [])
            return StockSamplingHelper.sample_blacklist(all_stock_ids, blacklist, sampling_amount)
        
        else:
            logger.warning(f"未知的采样策略: {sampling_strategy}，使用全部股票")
            return all_stock_ids[:sampling_amount]
    
    @staticmethod
    def sample_uniform(stock_ids: List[str], amount: int) -> List[str]:
        """均匀采样：每间隔 N 个股票抽取一个"""
        if amount >= len(stock_ids):
            return stock_ids
        
        step = len(stock_ids) // amount
        return [stock_ids[i * step] for i in range(amount)]
    
    @staticmethod
    def sample_stratified(stocks: List[Dict], amount: int, seed: int = None) -> List[str]:
        """分层采样：按市场类型（沪深主板，中小板，创业板，科创板）"""
        import random
        if seed is not None:
            random.seed(seed)
        
        # 按市场分组
        market_groups = {}
        for stock in stocks:
            stock_id = stock['id']
            # 根据股票代码判断市场
            if stock_id.endswith('.SH'):
                if stock_id.startswith('688'):
                    market = '科创板'
                elif stock_id.startswith('60'):
                    market = '沪市主板'
                else:
                    market = '其他沪市'
            elif stock_id.endswith('.SZ'):
                if stock_id.startswith('300'):
                    market = '创业板'
                elif stock_id.startswith('002'):
                    market = '中小板'
                elif stock_id.startswith('000'):
                    market = '深市主板'
                else:
                    market = '其他深市'
            else:
                market = '其他'
            
            if market not in market_groups:
                market_groups[market] = []
            market_groups[market].append(stock_id)
        
        # 按比例从每个市场抽取
        result = []
        total_stocks = len(stocks)
        for market, stock_ids in market_groups.items():
            market_ratio = len(stock_ids) / total_stocks
            market_amount = max(1, int(amount * market_ratio))
            sampled = random.sample(stock_ids, min(market_amount, len(stock_ids)))
            result.extend(sampled)
        
        # 如果抽取不足，随机补充
        if len(result) < amount:
            all_ids = [s['id'] for s in stocks]
            remaining = [sid for sid in all_ids if sid not in result]
            additional = random.sample(remaining, min(amount - len(result), len(remaining)))
            result.extend(additional)
        
        return result[:amount]
    
    @staticmethod
    def sample_random(stock_ids: List[str], amount: int, seed: int = None) -> List[str]:
        """随机采样"""
        import random
        if seed is not None:
            random.seed(seed)
        
        return random.sample(stock_ids, min(amount, len(stock_ids)))
    
    @staticmethod
    def sample_continuous(stock_ids: List[str], amount: int, start_idx: int) -> List[str]:
        """连续采样：从 start_idx 开始取 amount 个"""
        end_idx = min(start_idx + amount, len(stock_ids))
        return stock_ids[start_idx:end_idx]
    
    @staticmethod
    def sample_pool(stock_pool: List[str], amount: int) -> List[str]:
        """股票池采样：从指定股票池中抽取"""
        return stock_pool[:amount]
    
    @staticmethod
    def sample_blacklist(stock_ids: List[str], blacklist: List[str], amount: int) -> List[str]:
        """黑名单采样：排除黑名单后抽取"""
        filtered = [sid for sid in stock_ids if sid not in blacklist]
        return filtered[:amount]
