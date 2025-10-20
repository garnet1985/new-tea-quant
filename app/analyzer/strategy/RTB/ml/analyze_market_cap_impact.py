#!/usr/bin/env python3
"""
RTB策略市值标签影响分析 - V19.0简化版
只分析市值标签对策略表现的影响
"""

import os
import json
from typing import Dict, List, Any
from loguru import logger
from collections import defaultdict
from datetime import datetime

class MarketCapImpactAnalyzer:
    def __init__(self, strategy_folder_name: str):
        self.strategy_folder_name = strategy_folder_name
        self.results_dir = self._get_results_directory()
        logger.info(f"初始化市值标签影响分析器，结果目录: {self.results_dir}")

    def _get_results_directory(self) -> str:
        """获取模拟结果的根目录"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 从当前文件位置向上找到项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
        strategy_dir = os.path.join(project_root, "analyzer", "strategy", self.strategy_folder_name)
        tmp_dir = os.path.join(strategy_dir, "tmp")
        return tmp_dir

    def analyze(self):
        """执行市值标签影响分析"""
        logger.info("🔍 开始分析RTB策略市值标签影响...")
        
        latest_session_dir = self._get_latest_session_directory()
        if not latest_session_dir:
            logger.error("❌ 未找到模拟结果目录")
            return
        
        logger.info(f"分析最新会话: {latest_session_dir}")
        
        all_investments = []
        for filename in os.listdir(latest_session_dir):
            if filename.endswith(".json") and filename != "0_session_summary.json":
                file_path = os.path.join(latest_session_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    stock_summary = json.load(f)
                    if 'investments' in stock_summary:
                        all_investments.extend(stock_summary['investments'])
        
        if not all_investments:
            logger.warning("⚠️ 未找到任何投资记录进行分析。")
            return
        
        self._analyze_market_cap_impact(all_investments)
        
        logger.info("✅ 市值标签影响分析完成。")

    def _get_latest_session_directory(self) -> str:
        """获取最新的模拟会话目录"""
        if not os.path.exists(self.results_dir):
            return None
        
        session_dirs = [
            os.path.join(self.results_dir, d) 
            for d in os.listdir(self.results_dir) 
            if os.path.isdir(os.path.join(self.results_dir, d)) and d.startswith(datetime.now().strftime('%Y_%m_%d'))
        ]
        
        if not session_dirs:
            return None
        
        # 按名称排序，通常最新的会在最后
        session_dirs.sort()
        return session_dirs[-1]

    def _analyze_market_cap_impact(self, investments: List[Dict[str, Any]]):
        """
        分析市值标签与投资表现的关系
        
        Args:
            investments: 投资记录列表
        """
        # 市值标签表现统计
        market_cap_performance = defaultdict(lambda: {
            'total_roi': 0.0, 
            'count': 0, 
            'total_profit': 0.0, 
            'total_loss': 0.0, 
            'win_count': 0, 
            'loss_count': 0,
            'total_duration': 0
        })
        
        # 统计有标签和无标签的投资
        labeled_investments = 0
        unlabeled_investments = 0
        
        for inv in investments:
            extra_fields = inv.get('extra_fields', {})
            labels = extra_fields.get('labels', {})
            overall_profit_rate = inv.get('overall_profit_rate', 0.0)
            duration = inv.get('duration_in_days', 0)
            
            # 检查是否有市值标签
            market_cap_labels = labels.get('market_cap', [])
            
            if market_cap_labels:
                labeled_investments += 1
                # 只分析市值标签
                for label_id in market_cap_labels:
                    market_cap_performance[label_id]['total_roi'] += overall_profit_rate
                    market_cap_performance[label_id]['count'] += 1
                    market_cap_performance[label_id]['total_duration'] += duration
                    
                    if overall_profit_rate > 0:
                        market_cap_performance[label_id]['win_count'] += 1
                        market_cap_performance[label_id]['total_profit'] += overall_profit_rate
                    else:
                        market_cap_performance[label_id]['loss_count'] += 1
                        market_cap_performance[label_id]['total_loss'] += overall_profit_rate
            else:
                unlabeled_investments += 1
        
        logger.info(f"\n--- 市值标签影响分析结果 (V19.0简化版) ---")
        logger.info(f"有标签的投资: {labeled_investments} 个")
        logger.info(f"无标签的投资: {unlabeled_investments} 个")
        logger.info(f"标签覆盖率: {labeled_investments / (labeled_investments + unlabeled_investments) * 100:.1f}%")
        
        if market_cap_performance:
            sorted_labels = sorted(market_cap_performance.items(), 
                                 key=lambda item: item[1]['total_roi'] / item[1]['count'] if item[1]['count'] > 0 else -float('inf'), 
                                 reverse=True)
            
            logger.info("\n市值标签表现排序:")
            logger.info(f"{'标签':<12} {'投资次数':<8} {'平均ROI':<10} {'胜率':<8} {'平均盈利':<10} {'平均亏损':<10} {'平均天数':<8}")
            logger.info("-" * 80)
            
            for label, data in sorted_labels:
                avg_roi = (data['total_roi'] / data['count']) * 100 if data['count'] > 0 else 0
                win_rate = (data['win_count'] / data['count']) * 100 if data['count'] > 0 else 0
                avg_profit = (data['total_profit'] / data['win_count']) * 100 if data['win_count'] > 0 else 0
                avg_loss = (data['total_loss'] / data['loss_count']) * 100 if data['loss_count'] > 0 else 0
                avg_duration = data['total_duration'] / data['count'] if data['count'] > 0 else 0
                
                logger.info(f"{label:<12} {data['count']:<8} {avg_roi:<9.2f}% {win_rate:<7.1f}% {avg_profit:<9.2f}% {avg_loss:<9.2f}% {avg_duration:<7.1f}")
            
            # 分析结论
            self._generate_insights(market_cap_performance)
        else:
            logger.warning("⚠️ 没有找到市值标签数据")

    def _generate_insights(self, market_cap_performance: Dict[str, Any]):
        """生成分析洞察"""
        logger.info("\n--- 分析洞察 ---")
        
        # 找出表现最好和最差的市值标签
        best_label = max(market_cap_performance.items(), 
                        key=lambda item: item[1]['total_roi'] / item[1]['count'] if item[1]['count'] > 0 else -float('inf'))
        worst_label = min(market_cap_performance.items(), 
                         key=lambda item: item[1]['total_roi'] / item[1]['count'] if item[1]['count'] > 0 else float('inf'))
        
        best_roi = (best_label[1]['total_roi'] / best_label[1]['count']) * 100 if best_label[1]['count'] > 0 else 0
        worst_roi = (worst_label[1]['total_roi'] / worst_label[1]['count']) * 100 if worst_label[1]['count'] > 0 else 0
        
        logger.info(f"🏆 表现最佳: {best_label[0]} (平均ROI: {best_roi:.2f}%)")
        logger.info(f"📉 表现最差: {worst_label[0]} (平均ROI: {worst_roi:.2f}%)")
        
        # 分析胜率
        best_win_rate_label = max(market_cap_performance.items(), 
                                 key=lambda item: item[1]['win_count'] / item[1]['count'] if item[1]['count'] > 0 else 0)
        best_win_rate = (best_win_rate_label[1]['win_count'] / best_win_rate_label[1]['count']) * 100 if best_win_rate_label[1]['count'] > 0 else 0
        
        logger.info(f"🎯 胜率最高: {best_win_rate_label[0]} (胜率: {best_win_rate:.1f}%)")
        
        # 分析投资周期
        longest_duration_label = max(market_cap_performance.items(), 
                                   key=lambda item: item[1]['total_duration'] / item[1]['count'] if item[1]['count'] > 0 else 0)
        longest_duration = longest_duration_label[1]['total_duration'] / longest_duration_label[1]['count'] if longest_duration_label[1]['count'] > 0 else 0
        
        logger.info(f"⏰ 投资周期最长: {longest_duration_label[0]} (平均: {longest_duration:.1f}天)")

if __name__ == "__main__":
    analyzer = MarketCapImpactAnalyzer(strategy_folder_name="RTB")
    analyzer.analyze()
