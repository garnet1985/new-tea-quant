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
            
            # 优先级3: 使用 start_idx 和 test_amount 进行范围测试
            elif mode_config.get('test_amount', 0) > 0:
                start_idx = mode_config.get('start_idx', 0)
                test_amount = mode_config.get('test_amount', 0)
                stock_list = stock_list[start_idx:start_idx + test_amount]
                logger.info(f"🔢 使用范围测试模式，从索引 {start_idx} 开始模拟 {len(stock_list)} 只股票")
            
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