#!/usr/bin/env python3
"""
Job Builder Helper - 作业构建助手

职责：
- 构建 Scanner 作业
- 构建 Simulator 作业
"""

from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class JobBuilderHelper:
    """作业构建助手"""
    
    @staticmethod
    def build_scan_jobs(
        stock_list: List[str],
        strategy_info: Dict[str, Any],
        date: str
    ) -> List[Dict[str, Any]]:
        """
        构建扫描作业
        
        每个股票一个 job
        
        Args:
            stock_list: 股票列表 ['000001.SZ', '000002.SZ', ...]
            strategy_info: 策略信息
            date: 扫描日期
        
        Returns:
            jobs: [
                {
                    'stock_id': '000001.SZ',
                    'execution_mode': 'scan',
                    'strategy_name': 'momentum',
                    'settings': {...},
                    'scan_date': '20251219',
                    'worker_module_path': 'app.userspace.strategies.momentum.strategy_worker',
                    'worker_class_name': 'MomentumStrategyWorker'
                },
                ...
            ]
        """
        from app.core.modules.strategy.enums import ExecutionMode
        
        jobs = []
        
        for stock_id in stock_list:
            job = {
                'stock_id': stock_id,
                'execution_mode': ExecutionMode.SCAN.value,
                'strategy_name': strategy_info['name'],
                'settings': strategy_info['settings'].to_dict(),
                'scan_date': date,
                'worker_module_path': strategy_info['worker_module_path'],
                'worker_class_name': strategy_info['worker_class_name']
            }
            jobs.append(job)
        
        return jobs
    
    @staticmethod
    def build_simulate_jobs(
        stock_list: List[str],
        strategy_info: Dict[str, Any],
        session_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        构建模拟作业（历史回测）
        
        每个股票一个 job，在历史数据上逐日运行
        
        Args:
            stock_list: 股票列表 ['000001.SZ', '000002.SZ', ...]
            strategy_info: 策略信息
            session_id: Session ID
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        Returns:
            jobs: [
                {
                    'stock_id': '000001.SZ',
                    'execution_mode': 'simulate',
                    'strategy_name': 'momentum',
                    'settings': {...},
                    'session_id': 'sim_20251219_123456',
                    'start_date': '20230101',
                    'end_date': '20251219',
                    'worker_module_path': 'app.userspace.strategies.momentum.strategy_worker',
                    'worker_class_name': 'MomentumStrategyWorker'
                },
                ...
            ]
        """
        from app.core.modules.strategy.enums import ExecutionMode
        
        jobs = []
        
        for stock_id in stock_list:
            job = {
                'stock_id': stock_id,
                'execution_mode': ExecutionMode.SIMULATE.value,
                'strategy_name': strategy_info['name'],
                'settings': strategy_info['settings'].to_dict(),
                'session_id': session_id,
                'start_date': start_date,
                'end_date': end_date,
                'worker_module_path': strategy_info['worker_module_path'],
                'worker_class_name': strategy_info['worker_class_name']
            }
            jobs.append(job)
        
        return jobs
