#!/usr/bin/env python3
"""
投资记录器 - 记录投资结算信息
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

from app.data_source.data_source_service import DataSourceService
from .strategy_settings import strategy_settings
# 导入策略设置
class InvestmentRecorder:
    """投资记录器 - 记录投资结算信息"""
    
    def __init__(self, base_dir: str = "tmp"):
        """
        初始化投资记录器
        
        Args:
            base_dir: 基础目录路径
        """
        self.record_root = base_dir
        self.meta_file = os.path.join(self.record_root, "meta.json")

        # 确保基础目录存在
        os.makedirs(base_dir, exist_ok=True)

        self.current_session_id = self._create_new_session_id()

        self.cached_investments = {}
        


    def to_record(self, stock_info: Dict[str, Any], investment_history: List[Dict[str, Any]]):
        """
        记录单只股票的投资历史
        
        Args:
            stock_info: 股票信息
            investment_history: 投资历史记录
        """
        code, market = DataSourceService.parse_ts_code(stock_info.get('id', ''))
        
        # 计算统计信息
        total_investments = len(investment_history)
        success_count = len([inv for inv in investment_history if inv.get('status') == 'win'])
        fail_count = len([inv for inv in investment_history if inv.get('status') == 'loss'])
        open_count = len([inv for inv in investment_history if inv.get('status') == 'open'])
        
        # 计算胜率
        win_rate = (success_count / total_investments * 100) if total_investments > 0 else 0.0
        
        # 计算总收益和平均收益
        total_profit = sum([inv.get('settlement_info', {}).get('profit_loss', 0) for inv in investment_history])
        avg_profit = total_profit / total_investments if total_investments > 0 else 0.0
        
        # 计算平均投资时长
        durations = [inv.get('settlement_info', {}).get('duration_days', 0) for inv in investment_history if inv.get('settlement_info', {}).get('duration_days')]
        avg_duration_days = sum(durations) / len(durations) if durations else 0.0
        
        record = {
            'stock_info': {
                'id': stock_info.get('id', ''),
                'name': stock_info.get('name', ''),
                'industry': stock_info.get('industry', ''),
                'code': code,
                'market': market,
            },
            'results': investment_history,
            'statistics': {
                'total_investments': total_investments,
                'success_count': success_count,
                'fail_count': fail_count,
                'open_count': open_count,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'avg_profit': avg_profit,
                'avg_duration_days': avg_duration_days
            }
        }

        # 缓存投资记录
        self.cached_investments[stock_info.get('id', '')] = investment_history

        # 保存到文件
        self._save_record(record)
        

    def _save_record(self, record: Dict[str, Any]):
        """保存单只股票的投资记录"""
        file_name = f"{record.get('stock_info', {}).get('id', '')}.json"
        session_dir = os.path.join(self.record_root, self._get_session_folder_name())
        
        # 确保会话目录存在
        os.makedirs(session_dir, exist_ok=True)
        
        file_path = os.path.join(session_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(record, file, ensure_ascii=False, indent=2)

    
    def to_session(self, stocks):
        success_count = 0
        fail_count = 0
        open_count = 0
        total_profit = 0.0
        total_duration = 0
        total_investments = 0
        
        # 统计每只股票的投资结果
        for stock_id, investment_history in self.cached_investments.items():
            for investment in investment_history:
                total_investments += 1
                status = investment.get('status', '')
                
                if status == 'win':
                    success_count += 1
                    total_profit += investment.get('settlement_info', {}).get('profit_loss', 0)
                elif status == 'loss':
                    fail_count += 1
                    total_profit += investment.get('settlement_info', {}).get('profit_loss', 0)
                elif status == 'open':
                    open_count += 1
                
                # 累计投资时长
                duration = investment.get('settlement_info', {}).get('duration_days', 0)
                if duration:
                    total_duration += duration
        
        # 计算统计信息
        win_rate = (success_count / total_investments * 100) if total_investments > 0 else 0.0
        avg_duration = (total_duration / total_investments) if total_investments > 0 else 0.0
        avg_profit = (total_profit / total_investments) if total_investments > 0 else 0.0
        
        # 创建会话汇总
        session_summary = {
            'session_id': self.current_session_id,
            'session_name': self._get_session_folder_name(),
            'created_at': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y_%m_%d'),
            'description': 'HistoricLow策略投资记录会话',
            'total_stocks_tested': len(stocks),
            'investment_summary': {
                'total_investment_count': total_investments,
                'success_count': success_count,
                'fail_count': fail_count,
                'open_count': open_count,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'avg_profit': avg_profit,
                'avg_duration_days': avg_duration
            },
            'strategy_settings': strategy_settings
        }
        
        # 保存会话汇总
        self._save_session_summary(session_summary)
        
        # 更新meta文件
        self._update_meta_file()
        
        return session_summary



    def _create_new_session_id(self):
        """从meta.json获取下一个会话ID"""
        if not os.path.exists(self.meta_file):
            # 如果meta.json不存在，创建初始文件
            self._init_meta_file()

        with open(self.meta_file, "r", encoding="utf-8") as file:
            meta = json.load(file)

        return meta.get("next_session_id", 0)

    def _save_session_summary(self, session_summary: Dict[str, Any]):
        """保存会话汇总信息"""
        session_dir = os.path.join(self.record_root, self._get_session_folder_name())
        os.makedirs(session_dir, exist_ok=True)
        
        summary_file = os.path.join(session_dir, "session_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(session_summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📝 会话汇总已保存: {summary_file}")

    def _get_session_folder_name(self):
        """获取记录名称"""
        return f"{datetime.now().strftime('%Y_%m_%d')}-{self.current_session_id}"


    def _init_meta_file(self):
        meta = {
            "next_session_id": 1,
            "last_updated": datetime.now().isoformat()
        }
        with open(self.meta_file, "w", encoding="utf-8") as file:
            json.dump(meta, file, ensure_ascii=False, indent=2)

    def _update_meta_file(self):
        meta = {
            "next_session_id": self.current_session_id + 1,
            "last_updated": datetime.now().isoformat()
        }
        with open(self.meta_file, "w", encoding="utf-8") as file:
            json.dump(meta, file, ensure_ascii=False, indent=2)