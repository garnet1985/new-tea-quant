#!/usr/bin/env python3
"""
策略管理器 - 统一管理所有策略的初始化、注册和调度
"""
from typing import Dict, List, Any, Type
from loguru import logger
from utils.db.db_manager import DatabaseManager
from .base_strategy import BaseStrategy


class StrategyManager:
    """策略管理器 - 统一管理所有策略"""
    
    def __init__(self, connected_db: DatabaseManager, is_verbose: bool = False):
        """
        初始化策略管理器
        
        Args:
            db_manager: 已初始化的数据库管理器实例
        """
        self.db = connected_db
        self.is_verbose = is_verbose
        
        # 注册的策略类
        self._registered_strategies: Dict[str, Type[BaseStrategy]] = {}
        
        # 实例化的策略对象
        self._strategy_instances: Dict[str, BaseStrategy] = {}
        
        self.initialize()

    def initialize(self):
        """初始化策略管理器"""
        self._register_builtin_strategies()
        self.initialize_strategies()
    
    def _register_builtin_strategies(self):
        """注册内置策略"""
        try:
            # 注册 HistoricLow 策略
            from .historicLow.historic_low import HistoricLowStrategy
            self.register_strategy('historic_low', HistoricLowStrategy)
            
            # 可以在这里添加其他策略的注册
            # from .lowPrice.low_price import LowPriceStrategy
            # self.register_strategy('low_price', LowPriceStrategy)
            
        except ImportError as e:
            logger.warning(f"⚠️ 某些策略模块导入失败: {e}")
    
    def register_strategy(self, strategy_key: str, strategy_class: Type[BaseStrategy]):
        """
        注册策略类
        
        Args:
            strategy_key: 策略标识符
            strategy_class: 策略类
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"策略类 {strategy_class} 必须继承 BaseStrategy")
        
        self._registered_strategies[strategy_key] = strategy_class
        if self.is_verbose:
            logger.info(f"📝 注册策略: {strategy_key} -> {strategy_class.__name__}")
    
    def initialize_strategies(self) -> None:
        """初始化所有已注册的策略"""
        if self.is_verbose:
            logger.info("🚀 开始初始化所有策略...")
        
        for strategy_key, strategy_class in self._registered_strategies.items():
            try:
                # 实例化策略
                strategy_instance = strategy_class(self.db)
                self._strategy_instances[strategy_key] = strategy_instance
                
                if self.is_verbose:
                    logger.info(f"✅ 策略初始化成功: {strategy_key}")
                    
            except Exception as e:
                logger.error(f"❌ 策略初始化失败 {strategy_key}: {e}")
                raise
        
        if self.is_verbose:
            logger.info(f"🎉 所有策略初始化完成，共 {len(self._strategy_instances)} 个策略")
    
    def get_strategy(self, strategy_key: str) -> BaseStrategy:
        """
        获取策略实例
        
        Args:
            strategy_key: 策略标识符
            
        Returns:
            BaseStrategy: 策略实例
        """
        if strategy_key not in self._strategy_instances:
            raise KeyError(f"策略 {strategy_key} 未找到，请确保已初始化")
        
        return self._strategy_instances[strategy_key]
    
    def get_all_strategies(self) -> Dict[str, BaseStrategy]:
        """获取所有策略实例"""
        return self._strategy_instances.copy()
    
    def get_strategy_info(self) -> List[Dict[str, Any]]:
        """获取所有策略的信息"""
        return [
            {
                'key': key,
                'info': strategy.get_strategy_info()
            }
            for key, strategy in self._strategy_instances.items()
        ]
    
    def scan_all_strategies(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        扫描所有策略的投资机会
        
        Returns:
            Dict[str, List[Dict]]: 每个策略的扫描结果
        """
        results = {}
        
        for strategy_key, strategy in self._strategy_instances.items():
            try:
                if self.is_verbose:
                    logger.info(f"🔍 开始扫描策略: {strategy_key}")
                
                opportunities = strategy.scan()
                results[strategy_key] = opportunities
                
                if self.is_verbose:
                    logger.info(f"✅ 策略 {strategy_key} 扫描完成，发现 {len(opportunities)} 个机会")
                    
            except Exception as e:
                logger.error(f"❌ 策略 {strategy_key} 扫描失败: {e}")
                results[strategy_key] = []
        
        return results
    
    def report_all_strategies(self, results: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        呈现所有策略的扫描结果
        
        Args:
            results: 扫描结果字典
        """
        for strategy_key, opportunities in results.items():
            try:
                strategy = self.get_strategy(strategy_key)
                strategy.report(opportunities)
            except Exception as e:
                logger.error(f"❌ 策略 {strategy_key} 报告生成失败: {e}")
    
    def test_all_strategies(self) -> None:
        """测试所有策略"""
        for strategy_key, strategy in self._strategy_instances.items():
            try:
                if self.is_verbose:
                    logger.info(f"🧪 开始测试策略: {strategy_key}")
                
                strategy.test()
                
                if self.is_verbose:
                    logger.info(f"✅ 策略 {strategy_key} 测试完成")
                    
            except Exception as e:
                logger.error(f"❌ 策略 {strategy_key} 测试失败: {e}")
    
    def run_daily_scan(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        执行每日扫描 - 扫描所有策略并生成报告
        
        Returns:
            Dict[str, List[Dict]]: 扫描结果
        """
        if self.is_verbose:
            logger.info("🌅 开始执行每日策略扫描...")
        
        # 扫描所有策略
        results = self.scan_all_strategies()
        
        # 生成报告
        self.report_all_strategies(results)
        
        if self.is_verbose:
            total_opportunities = sum(len(opps) for opps in results.values())
            logger.info(f"🎉 每日扫描完成，总共发现 {total_opportunities} 个投资机会")
        
        return results 