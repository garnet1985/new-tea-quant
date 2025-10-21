#!/usr/bin/env python3
"""
改进股票采样策略 - 解决连续采样导致的样本偏差问题
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import random
import math
from typing import List, Dict, Any
from loguru import logger

class StockSamplingStrategy:
    """股票采样策略"""
    
    @staticmethod
    def uniform_sampling(stock_list: List[Dict[str, Any]], sample_size: int, seed: int = 42) -> List[Dict[str, Any]]:
        """
        均匀间隔采样 - 保证样本分布均匀，结果可重现
        
        Args:
            stock_list: 完整股票列表
            sample_size: 采样数量
            seed: 随机种子（用于可重现性）
            
        Returns:
            List[Dict]: 采样后的股票列表
        """
        total_stocks = len(stock_list)
        
        if sample_size >= total_stocks:
            logger.warning(f"采样数量({sample_size}) >= 总股票数({total_stocks})，返回完整列表")
            return stock_list
        
        # 计算采样间隔
        step = total_stocks / sample_size
        
        # 生成均匀分布的索引
        indices = []
        for i in range(sample_size):
            # 使用固定偏移避免总是从0开始
            offset = i * step
            index = int(offset + (step * 0.5))  # 取间隔中点
            indices.append(index)
        
        # 提取采样股票
        sampled_stocks = [stock_list[idx] for idx in indices if idx < total_stocks]
        
        logger.info(f"均匀采样: 从{total_stocks}只股票中采样{sample_size}只")
        logger.info(f"采样间隔: {step:.2f}")
        logger.info(f"实际采样数量: {len(sampled_stocks)}")
        
        return sampled_stocks
    
    @staticmethod
    def stratified_sampling(stock_list: List[Dict[str, Any]], sample_size: int, seed: int = 42) -> List[Dict[str, Any]]:
        """
        分层采样 - 按股票代码前缀分层，确保不同市场都有代表
        
        Args:
            stock_list: 完整股票列表
            sample_size: 采样数量
            seed: 随机种子
            
        Returns:
            List[Dict]: 采样后的股票列表
        """
        # 按股票代码前缀分组
        groups = {}
        for stock in stock_list:
            stock_id = stock['id']
            prefix = stock_id[:2]  # 取前两位作为分组依据
            
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(stock)
        
        logger.info(f"分层采样: 发现{len(groups)}个股票分组")
        for prefix, stocks in groups.items():
            logger.info(f"  {prefix}: {len(stocks)}只股票")
        
        # 按组大小分配采样数量
        sampled_stocks = []
        random.seed(seed)
        
        for prefix, stocks in groups.items():
            # 按比例分配采样数量
            group_sample_size = max(1, int(sample_size * len(stocks) / len(stock_list)))
            
            # 从该组中随机采样
            if group_sample_size >= len(stocks):
                sampled_stocks.extend(stocks)
            else:
                sampled_stocks.extend(random.sample(stocks, group_sample_size))
        
        # 如果采样数量不足，从剩余股票中补充
        if len(sampled_stocks) < sample_size:
            remaining_stocks = [s for s in stock_list if s not in sampled_stocks]
            additional_needed = sample_size - len(sampled_stocks)
            if additional_needed <= len(remaining_stocks):
                sampled_stocks.extend(random.sample(remaining_stocks, additional_needed))
        
        logger.info(f"分层采样: 实际采样{len(sampled_stocks)}只股票")
        return sampled_stocks
    
    @staticmethod
    def random_sampling(stock_list: List[Dict[str, Any]], sample_size: int, seed: int = 42) -> List[Dict[str, Any]]:
        """
        随机采样 - 完全随机，但使用固定种子保证可重现
        
        Args:
            stock_list: 完整股票列表
            sample_size: 采样数量
            seed: 随机种子
            
        Returns:
            List[Dict]: 采样后的股票列表
        """
        random.seed(seed)
        
        if sample_size >= len(stock_list):
            return stock_list
        
        sampled_stocks = random.sample(stock_list, sample_size)
        
        logger.info(f"随机采样: 从{len(stock_list)}只股票中随机采样{sample_size}只")
        return sampled_stocks
    
    @staticmethod
    def analyze_sampling_distribution(stock_list: List[Dict[str, Any]], sampled_stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析采样分布情况
        
        Args:
            stock_list: 完整股票列表
            sampled_stocks: 采样后的股票列表
            
        Returns:
            Dict: 分布分析结果
        """
        # 分析股票代码前缀分布
        full_distribution = {}
        sample_distribution = {}
        
        for stock in stock_list:
            prefix = stock['id'][:2]
            full_distribution[prefix] = full_distribution.get(prefix, 0) + 1
        
        for stock in sampled_stocks:
            prefix = stock['id'][:2]
            sample_distribution[prefix] = sample_distribution.get(prefix, 0) + 1
        
        # 计算覆盖率
        coverage = {}
        for prefix in full_distribution:
            full_count = full_distribution[prefix]
            sample_count = sample_distribution.get(prefix, 0)
            coverage[prefix] = sample_count / full_count if full_count > 0 else 0
        
        return {
            'full_distribution': full_distribution,
            'sample_distribution': sample_distribution,
            'coverage': coverage
        }


def test_sampling_strategies():
    """测试不同的采样策略"""
    
    # 模拟股票列表
    stock_list = []
    for i in range(4000):
        if i < 1000:
            stock_id = f"000{i:03d}.SZ"  # 深市主板
        elif i < 2000:
            stock_id = f"002{i-1000:03d}.SZ"  # 深市中小板
        elif i < 3000:
            stock_id = f"300{i-2000:03d}.SZ"  # 深市创业板
        else:
            stock_id = f"600{i-3000:03d}.SH"  # 沪市主板
        
        stock_list.append({
            'id': stock_id,
            'name': f'股票{i:04d}'
        })
    
    sample_size = 500
    
    print("=== 股票采样策略对比测试 ===")
    print(f"总股票数: {len(stock_list)}")
    print(f"采样数量: {sample_size}")
    print()
    
    # 测试连续采样（当前方式）
    continuous_samples = stock_list[:sample_size]
    print("1. 连续采样（当前方式）:")
    analysis = StockSamplingStrategy.analyze_sampling_distribution(stock_list, continuous_samples)
    for prefix, coverage in analysis['coverage'].items():
        if coverage > 0:
            print(f"   {prefix}: {analysis['sample_distribution'][prefix]}/{analysis['full_distribution'][prefix]} ({coverage:.1%})")
    print()
    
    # 测试均匀采样
    uniform_samples = StockSamplingStrategy.uniform_sampling(stock_list, sample_size)
    print("2. 均匀间隔采样:")
    analysis = StockSamplingStrategy.analyze_sampling_distribution(stock_list, uniform_samples)
    for prefix, coverage in analysis['coverage'].items():
        if coverage > 0:
            print(f"   {prefix}: {analysis['sample_distribution'][prefix]}/{analysis['full_distribution'][prefix]} ({coverage:.1%})")
    print()
    
    # 测试分层采样
    stratified_samples = StockSamplingStrategy.stratified_sampling(stock_list, sample_size)
    print("3. 分层采样:")
    analysis = StockSamplingStrategy.analyze_sampling_distribution(stock_list, stratified_samples)
    for prefix, coverage in analysis['coverage'].items():
        if coverage > 0:
            print(f"   {prefix}: {analysis['sample_distribution'][prefix]}/{analysis['full_distribution'][prefix]} ({coverage:.1%})")
    print()
    
    # 测试随机采样
    random_samples = StockSamplingStrategy.random_sampling(stock_list, sample_size)
    print("4. 随机采样:")
    analysis = StockSamplingStrategy.analyze_sampling_distribution(stock_list, random_samples)
    for prefix, coverage in analysis['coverage'].items():
        if coverage > 0:
            print(f"   {prefix}: {analysis['sample_distribution'][prefix]}/{analysis['full_distribution'][prefix]} ({coverage:.1%})")


if __name__ == "__main__":
    test_sampling_strategies()
