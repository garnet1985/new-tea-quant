#!/usr/bin/env python3
"""
PreprocessService - 预处理服务
"""
from typing import Dict, List, Any
from loguru import logger
from utils.icon.icon_service import IconService


class PreprocessService:
    """预处理服务 - 验证设置，获取股票列表"""
    
    @staticmethod
    def get_stock_list(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取股票列表 - 遵循与 BaseStrategy.scan 相同的优先级逻辑
        
        Args:
            settings: 策略设置
            
        Returns:
            List[Dict]: 股票列表
        """
        
        try:
            # 使用 DataLoader 加载股票列表
            from utils.db.db_manager import DatabaseManager
            from app.data_loader import DataLoader
            
            # 创建数据库连接
            db = DatabaseManager()
            db.initialize()
            
            # 使用 DataLoader 加载股票列表（使用过滤规则，排除ST、科创板等）
            loader = DataLoader(db)
            stock_list = loader.load_stock_list(filtered=True)
            
            # 根据 settings 的 mode 配置确定模拟范围
            mode_config = settings.get('mode', {})
            
            # 优先级1: 如果开启 blacklist_only，模拟黑名单股票
            if mode_config.get('blacklist_only', False):
                blacklist = settings.get('goal', {}).get('blacklist', {}).get('list', [])
                if blacklist:
                    stock_list = PreprocessService._filter_list_by_ids(stock_list, blacklist)
                    logger.info(f"📋 使用黑名单模式，模拟 {len(stock_list)} 只股票")
                else:
                    logger.warning("⚠️ 启用了黑名单模式但黑名单为空，将使用其他模式")
            
            # 优先级2: 使用 scan_stock_pool 指定的股票列表
            elif mode_config.get('scan_stock_pool'):
                scan_pool = mode_config.get('scan_stock_pool', [])
                if scan_pool:
                    stock_list = PreprocessService._filter_list_by_ids(stock_list, scan_pool)
                    logger.info(f"🎯 使用股票池模式，模拟 {len(stock_list)} 只股票")
            
            # 优先级3: 使用采样策略限制测试股票数量
            elif mode_config.get('test_amount', 0) > 0:
                test_amount = mode_config.get('test_amount', 0)
                
                # 获取采样配置
                sampling_config = settings.get('sampling', {})
                sampling_strategy = sampling_config.get('strategy', 'continuous')
                
                # 根据采样策略执行相应的采样方法
                if sampling_strategy == 'uniform':
                    # 均匀间隔采样
                    stock_list = PreprocessService._uniform_sampling(stock_list, test_amount)
                    logger.info(f"📊 均匀间隔采样: {len(stock_list)} 只股票")
                    
                elif sampling_strategy == 'stratified':
                    # 分层采样
                    stratified_config = sampling_config.get('stratified', {})
                    seed = stratified_config.get('seed', 42)
                    stock_list = PreprocessService._stratified_sampling(stock_list, test_amount, seed)
                    logger.info(f"📊 分层采样: {len(stock_list)} 只股票 (seed={seed})")
                    
                elif sampling_strategy == 'random':
                    # 随机采样
                    random_config = sampling_config.get('random', {})
                    seed = random_config.get('seed', 42)
                    stock_list = PreprocessService._random_sampling(stock_list, test_amount, seed)
                    logger.info(f"📊 随机采样: {len(stock_list)} 只股票 (seed={seed})")
                    
                else:  # continuous
                    # 连续采样（原有方式）
                    continuous_config = sampling_config.get('continuous', {})
                    start_idx = continuous_config.get('start_idx', 0)
                    stock_list = stock_list[start_idx:start_idx + test_amount]
                    logger.info(f"🔢 连续采样: {len(stock_list)} 只股票 (从索引 {start_idx} 开始)")
            
            # 优先级4: 模拟全部股票
            else:
                logger.info(f"🌐 使用全量模拟模式，模拟 {len(stock_list)} 只股票")
            
            return stock_list
            
        except Exception as e:
            logger.error(f"{IconService.get('error')} 获取股票列表失败: {e}")
            return []
    
    @staticmethod
    def _filter_list_by_ids(stock_list: List[Dict[str, Any]], stock_ids: List[str]) -> List[Dict[str, Any]]:
        """
        根据股票ID列表过滤股票
        """
        new_list = []
        for stock in stock_list:
            if stock.get('id') in stock_ids:
                new_list.append(stock)
        return new_list
    
    @staticmethod
    def _uniform_sampling(stock_list: List[Dict[str, Any]], sample_size: int) -> List[Dict[str, Any]]:
        """
        均匀间隔采样 - 保证样本分布均匀，结果可重现
        """
        total_stocks = len(stock_list)
        
        if sample_size >= total_stocks:
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
        
        return sampled_stocks
    
    @staticmethod
    def _stratified_sampling(stock_list: List[Dict[str, Any]], sample_size: int, seed: int = 42) -> List[Dict[str, Any]]:
        """
        分层采样 - 按股票代码前缀分层，确保不同市场都有代表
        """
        import random
        
        # 按股票代码前缀分组
        groups = {}
        for stock in stock_list:
            stock_id = stock['id']
            prefix = stock_id[:2]  # 取前两位作为分组依据
            
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(stock)
        
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
        
        return sampled_stocks
    
    @staticmethod
    def _random_sampling(stock_list: List[Dict[str, Any]], sample_size: int, seed: int = 42) -> List[Dict[str, Any]]:
        """
        随机采样 - 完全随机，但使用固定种子保证可重现
        """
        import random
        
        random.seed(seed)
        
        if sample_size >= len(stock_list):
            return stock_list
        
        sampled_stocks = random.sample(stock_list, sample_size)
        return sampled_stocks