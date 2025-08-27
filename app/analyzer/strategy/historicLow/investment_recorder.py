#!/usr/bin/env python3
"""
投资记录器 - 记录投资结算信息
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any
from loguru import logger

from app.data_source.data_source_service import DataSourceService
from .strategy_settings import strategy_settings
from .strategy_enum import InvestmentResult

class InvestmentRecorder:
    """投资记录器 - 记录投资结算信息"""
    
    def __init__(self):
        """初始化投资记录器"""
        # 设置tmp目录路径（在historicLow策略目录下）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.tmp_dir = os.path.join(current_dir, "tmp")
        self.meta_file = os.path.join(self.tmp_dir, "meta.json")
        
        # 确保tmp目录存在
        os.makedirs(self.tmp_dir, exist_ok=True)
        
        # 初始化meta.json文件
        self._init_meta_file()
        
        # 获取当前会话ID
        self.current_session_id = self._get_next_session_id()
        
        # 缓存投资记录
        self.cached_investments = {}
        


    def to_record(self, stock_info: Dict[str, Any], investment_history: List[Dict[str, Any]]):
        """
        记录单只股票的投资历史
        
        Args:
            stock_info: 股票信息
            investment_history: 投资历史记录
        """
        # 确保当前session文件夹存在
        session_dir = self._get_session_dir()
        os.makedirs(session_dir, exist_ok=True)
        
        # 解析股票代码
        code, market = DataSourceService.parse_ts_code(stock_info.get('id', ''))
        
        # 计算统计信息
        total_investments = len(investment_history)
        success_count = len([inv for inv in investment_history if inv.get('status') == InvestmentResult.WIN.value])
        fail_count = len([inv for inv in investment_history if inv.get('status') == InvestmentResult.LOSS.value])
        open_count = len([inv for inv in investment_history if inv.get('status') == InvestmentResult.OPEN.value])
        
        # 计算胜率
        win_rate = (success_count / total_investments * 100) if total_investments > 0 else 0.0
        
        # 计算总收益和平均收益
        total_profit = sum([inv.get('settlement_info', {}).get('profit_loss', 0) for inv in investment_history])
        avg_profit = total_profit / total_investments if total_investments > 0 else 0.0
        
        # 计算平均投资时长
        durations = [inv.get('settlement_info', {}).get('duration_days', 0) for inv in investment_history if inv.get('settlement_info', {}).get('duration_days')]
        avg_duration_days = sum(durations) / len(durations) if durations else 0.0
        
        # 构建记录数据
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
        self._save_stock_record(record)
        

    def to_session(self, stocks):
        """生成会话汇总"""
        # 统计所有投资记录
        stats = self._calculate_session_stats()
        
        # 创建会话汇总
        session_summary = {
            'session_id': self.current_session_id,
            'session_name': self._get_session_folder_name(),
            'created_at': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y_%m_%d'),
            'description': 'HistoricLow策略投资记录会话',
            'total_stocks_tested': len(stocks),
            'investment_summary': stats,
            'strategy_settings': strategy_settings
        }
        
        # 保存会话汇总
        self._save_session_summary(session_summary)
        
        # 更新meta文件
        self._update_meta_file()
        
        return session_summary



    def _save_stock_record(self, record: Dict[str, Any]):
        """保存单只股票的投资记录"""
        stock_id = record.get('stock_info', {}).get('id', '')
        file_name = f"{stock_id}.json"
        file_path = os.path.join(self._get_session_dir(), file_name)
        
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(record, file, ensure_ascii=False, indent=2)

    def _save_session_summary(self, session_summary: Dict[str, Any]):
        """保存会话汇总信息"""
        summary_file = os.path.join(self._get_session_dir(), "session_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(session_summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📝 会话汇总已保存: {summary_file}")

    def _get_session_dir(self):
        """获取当前会话目录路径"""
        session_name = f"{datetime.now().strftime('%Y_%m_%d')}-{self.current_session_id}"
        return os.path.join(self.tmp_dir, session_name)

    def _get_session_folder_name(self):
        """获取会话文件夹名称"""
        return f"{datetime.now().strftime('%Y_%m_%d')}-{self.current_session_id}"

    def _init_meta_file(self):
        """初始化meta.json文件"""
        if not os.path.exists(self.meta_file):
            meta = {
                "next_session_id": 1,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.meta_file, "w", encoding="utf-8") as file:
                json.dump(meta, file, ensure_ascii=False, indent=2)

    def _get_next_session_id(self):
        """获取下一个会话ID"""
        with open(self.meta_file, "r", encoding="utf-8") as file:
            meta = json.load(file)
        return meta.get("next_session_id", 1)

    def _update_meta_file(self):
        """更新meta.json文件"""
        meta = {
            "next_session_id": self.current_session_id + 1,
            "last_updated": datetime.now().isoformat()
        }
        with open(self.meta_file, "w", encoding="utf-8") as file:
            json.dump(meta, file, ensure_ascii=False, indent=2)

    def _calculate_session_stats(self):
        """计算会话统计信息"""
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
                
                if status == InvestmentResult.WIN.value:
                    success_count += 1
                    total_profit += investment.get('settlement_info', {}).get('profit_loss', 0)
                elif status == InvestmentResult.LOSS.value:
                    fail_count += 1
                    total_profit += investment.get('settlement_info', {}).get('profit_loss', 0)
                elif status == InvestmentResult.OPEN.value:
                    open_count += 1
                
                # 累计投资时长
                duration = investment.get('settlement_info', {}).get('duration_days', 0)
                if duration:
                    total_duration += duration
        
        # 计算统计信息
        win_rate = (success_count / total_investments * 100) if total_investments > 0 else 0.0
        avg_duration = (total_duration / total_investments) if total_investments > 0 else 0.0
        avg_profit = (total_profit / total_investments) if total_investments > 0 else 0.0
        
        return {
            'total_investment_count': total_investments,
            'success_count': success_count,
            'fail_count': fail_count,
            'open_count': open_count,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_duration_days': avg_duration
        }

