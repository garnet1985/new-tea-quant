#!/usr/bin/env python3
"""
HistoryLoader - 历史模拟结果加载器

职责：
- 加载 PriceFactorSimulator 的历史结果
- 计算每只股票的统计信息（胜率、平均收益等）
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class HistoryLoader:
    """历史模拟结果加载器"""
    
    @staticmethod
    def load_stock_history(
        strategy_name: str,
        stock_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        加载单只股票的历史模拟统计
        
        Args:
            strategy_name: 策略名称
            stock_id: 股票代码
        
        Returns:
            统计信息字典，如果不存在返回 None
            {
                'win_rate': 0.65,  # 胜率
                'avg_return': 0.05,  # 平均收益率
                'total_investments': 10,  # 总投资次数
                'win_count': 7,  # 盈利次数
                'loss_count': 3,  # 亏损次数
                'max_return': 0.15,  # 最大收益
                'min_return': -0.08,  # 最小收益
                'avg_holding_days': 5.2  # 平均持有天数
            }
        """
        try:
            # 1. 获取最新的 PriceFactorSimulator 版本
            from core.modules.strategy.managers.version_manager import VersionManager
            
            try:
                version_dir, _ = VersionManager.resolve_price_factor_version(
                    strategy_name=strategy_name,
                    version_spec="latest"
                )
            except (FileNotFoundError, ValueError) as e:
                logger.debug(f"[HistoryLoader] 无法获取最新模拟版本: {e}")
                return None
            
            # 2. 读取股票结果文件
            from core.modules.strategy.managers.result_path_manager import ResultPathManager
            path_manager = ResultPathManager(sim_version_dir=version_dir)
            stock_file = path_manager.stock_json_path(stock_id)
            
            if not stock_file.exists():
                return None
            
            # 3. 读取并解析 JSON
            with open(stock_file, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
            
            # 4. 提取投资记录
            investments = stock_data.get('investments', [])
            if not investments:
                return None
            
            # 5. 计算统计信息
            return HistoryLoader._calculate_statistics(investments)
            
        except Exception as e:
            logger.debug(f"[HistoryLoader] 加载股票历史失败: stock_id={stock_id}, error={e}")
            return None
    
    @staticmethod
    def _calculate_statistics(investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算投资统计信息
        
        Args:
            investments: 投资记录列表
        
        Returns:
            统计信息字典
        """
        if not investments:
            return {}
        
        # 过滤已完成的投资（result 为 win/loss，排除 open）
        completed = [
            inv for inv in investments
            if inv.get('result') in ['win', 'loss']
        ]
        
        if not completed:
            return {
                'total_investments': len(investments),
                'completed_investments': 0,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'win_count': 0,
                'loss_count': 0,
                'max_return': 0.0,
                'min_return': 0.0,
                'avg_holding_days': 0.0
            }
        
        # 提取收益率和统计
        returns = []
        holding_days = []
        win_count = 0
        loss_count = 0
        
        for inv in completed:
            # ROI 字段（PriceFactorSimulator 使用 roi）
            roi = inv.get('roi', 0.0)
            if not isinstance(roi, (int, float)):
                try:
                    roi = float(roi)
                except (ValueError, TypeError):
                    roi = 0.0
            
            returns.append(roi)
            
            # 根据 result 字段判断胜负
            result = inv.get('result', '')
            if result == 'win':
                win_count += 1
            elif result == 'loss':
                loss_count += 1
            # 如果 result 字段不可用，根据 ROI 判断
            elif roi > 0:
                win_count += 1
            elif roi < 0:
                loss_count += 1
            
            # 持有天数
            duration = inv.get('duration_in_days', 0)
            if not isinstance(duration, (int, float)):
                try:
                    duration = float(duration)
                except (ValueError, TypeError):
                    duration = 0.0
            
            if duration > 0:
                holding_days.append(duration)
        
        # 计算统计
        total = len(completed)
        win_rate = win_count / total if total > 0 else 0.0
        avg_return = sum(returns) / len(returns) if returns else 0.0
        max_return = max(returns) if returns else 0.0
        min_return = min(returns) if returns else 0.0
        avg_holding_days = sum(holding_days) / len(holding_days) if holding_days else 0.0
        
        return {
            'total_investments': len(investments),
            'completed_investments': total,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'win_count': win_count,
            'loss_count': loss_count,
            'max_return': max_return,
            'min_return': min_return,
            'avg_holding_days': avg_holding_days
        }
    
    @staticmethod
    def load_session_summary(strategy_name: str) -> Optional[Dict[str, Any]]:
        """
        加载最新的会话汇总
        
        Args:
            strategy_name: 策略名称
        
        Returns:
            会话汇总字典，如果不存在返回 None
        """
        try:
            from core.modules.strategy.managers.version_manager import VersionManager
            
            try:
                version_dir, _ = VersionManager.resolve_price_factor_version(
                    strategy_name=strategy_name,
                    version_spec="latest"
                )
            except (FileNotFoundError, ValueError) as e:
                logger.debug(f"[HistoryLoader] 无法获取最新模拟版本: {e}")
                return None
            
            from core.modules.strategy.managers.result_path_manager import ResultPathManager
            path_manager = ResultPathManager(sim_version_dir=version_dir)
            summary_file = path_manager.session_summary_path()
            
            if not summary_file.exists():
                return None
            
            with open(summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.debug(f"[HistoryLoader] 加载会话汇总失败: {e}")
            return None
