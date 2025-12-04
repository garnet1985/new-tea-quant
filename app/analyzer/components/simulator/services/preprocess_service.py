#!/usr/bin/env python3
"""
PreprocessService - 预处理服务
"""
from typing import Dict, List, Any
from loguru import logger
from utils.icon.icon_service import IconService
from app.analyzer.analyzer_service import AnalyzerService

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
            from app.data_manager import DataManager
            
            # 创建数据库连接
            db = DatabaseManager()
            db.initialize()
            
            # 使用 DataLoader 加载股票列表（使用过滤规则，排除ST、科创板等）
            loader = DataLoader(db)
            stock_list = loader.load_stock_list(filtered=True)
            
            # 使用AnalyzerService的统一采样方法
            stock_list = AnalyzerService.sample_stock_list(stock_list, settings)
            
            return stock_list
            
        except Exception as e:
            logger.error(f"{IconService.get('error')} 获取股票列表失败: {e}")
            return []
    