#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RTB策略参数网格搜索 - 为不同市值标签找到最优参数组合

目标：
- 为 large_cap, mid_cap, small_cap 分别找到最优的 convergence_days, stability_days, invest_range 参数
- 通过多次模拟，评估不同参数组合的表现
- 输出最优参数映射，用于实际策略中
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

from loguru import logger

# 允许从项目根目录运行
PROJECT_ROOT = Path(__file__).resolve().parents[4]
import sys
sys.path.append(str(PROJECT_ROOT))

from app.analyzer.components.simulator.simulator import Simulator


class ParamGridSearch:
    def __init__(self):
        self.strategy_dir = PROJECT_ROOT / 'app' / 'analyzer' / 'strategy' / 'RTB'
        self.tmp_dir = self.strategy_dir / 'tmp'
        self.rtb_file = self.strategy_dir / 'RTB.py'
        
        # 备份原始RTB.py文件
        self.backup_file = self.strategy_dir / 'RTB.py.backup'
        if not self.backup_file.exists():
            shutil.copy2(self.rtb_file, self.backup_file)
            logger.info(f"已备份原始RTB.py到 {self.backup_file}")
    
    def restore_original_file(self):
        """恢复原始RTB.py文件"""
        if self.backup_file.exists():
            shutil.copy2(self.backup_file, self.rtb_file)
            logger.info("已恢复原始RTB.py文件")
    
    def update_rtb_parameters(self, market_cap: str, conv_days: int, stab_days: int, 
                             invest_range_lower: float, invest_range_upper: float):
        """更新RTB.py文件中的参数映射"""
        content = self.rtb_file.read_text(encoding='utf-8')
        
        # 构建新的参数映射
        new_params = f"""                '{market_cap}': {{
                    'convergence_days': {conv_days},  # 优化后的收敛期
                    'stability_days': {stab_days},    # 优化后的稳定性要求
                    'invest_range_lower': {invest_range_lower},  # 优化后的买入区间下限
                    'invest_range_upper': {invest_range_upper},  # 优化后的买入区间上限
                }},"""
        
        # 使用正则表达式替换对应的参数映射
        import re
        pattern = rf"'{market_cap}':\s*{{\s*'convergence_days':\s*\d+.*?}}"
        content = re.sub(pattern, new_params.strip(), content, flags=re.DOTALL)
        
        # 写回文件
        self.rtb_file.write_text(content, encoding='utf-8')
        logger.debug(f"已更新 {market_cap} 参数: conv={conv_days}, stab={stab_days}, range=({invest_range_lower}, {invest_range_upper})")
    
    def run_simulation(self) -> Path:
        """运行一次RTB模拟，返回最新会话目录"""
        simulator = Simulator()
        module_info = {
            'strategy_module_path': 'app.analyzer.strategy.RTB.RTB',
            'strategy_class_name': 'ReverseTrendBet',
            'strategy_settings_path': 'app.analyzer.strategy.RTB.settings',
            'strategy_folder_name': 'RTB',
        }
        
        report = simulator.run(module_info)
        logger.info(f"模拟完成 - 总投资: {report.get('total_investments')}, 胜率: {report.get('win_rate'):.2%}")
        
        # 获取最新会话目录
        return self._get_latest_session_dir()
    
    def _get_latest_session_dir(self) -> Path:
        """获取最新的模拟会话目录"""
        if not self.tmp_dir.exists():
            return None
        
        today_prefix = datetime.now().strftime('%Y_%m_%d')
        session_dirs = [d for d in self.tmp_dir.iterdir() 
                       if d.is_dir() and d.name.startswith(today_prefix)]
        
        if not session_dirs:
            return None
        
        session_dirs.sort()
        return session_dirs[-1]
    
    def load_investments(self, session_dir: Path) -> List[Dict[str, Any]]:
        """加载投资记录"""
        investments = []
        for f in session_dir.iterdir():
            if f.is_file() and f.suffix == '.json' and f.name != '0_session_summary.json':
                try:
                    data = json.loads(f.read_text(encoding='utf-8'))
                    invs = data.get('investments', [])
                    if invs:
                        investments.extend(invs)
                except Exception as e:
                    logger.warning(f"读取文件失败 {f}: {e}")
        return investments
    
    def evaluate_label_performance(self, investments: List[Dict[str, Any]], label_name: str) -> Tuple[float, float, int]:
        """评估特定标签的投资表现"""
        filtered = []
        for inv in investments:
            labels = (inv.get('extra_fields') or {}).get('labels') or {}
            market_caps = labels.get('market_cap') or []
            if label_name in market_caps:
                filtered.append(inv)
        
        if not filtered:
            return 0.0, 0.0, 0
        
        total = len(filtered)
        avg_roi = sum(inv.get('overall_profit_rate', 0.0) for inv in filtered) / total
        win_count = sum(1 for inv in filtered if inv.get('overall_profit_rate', 0.0) > 0)
        win_rate = win_count / total
        
        return avg_roi, win_rate, total
    
    def search_optimal_params(self):
        """执行参数网格搜索"""
        logger.info("🚀 开始RTB策略参数网格搜索...")
        
        # 定义搜索网格
        convergence_candidates = [15, 20, 25, 30]
        stability_candidates = [8, 10, 12, 15]
        invest_range_candidates = [
            (0.008, 0.008), (0.01, 0.01), (0.012, 0.012), 
            (0.015, 0.015), (0.02, 0.02)
        ]
        
        labels = ['large_cap', 'mid_cap', 'small_cap']
        optimal_params = {}
        
        # 为每个标签搜索最优参数
        for label in labels:
            logger.info(f"\n🔍 开始搜索 {label} 的最优参数...")
            
            best_score = (-1e9, -1.0)  # (avg_roi, win_rate)
            best_params = None
            total_combinations = len(convergence_candidates) * len(stability_candidates) * len(invest_range_candidates)
            current_combination = 0
            
            for conv_days in convergence_candidates:
                for stab_days in stability_candidates:
                    for ir_lower, ir_upper in invest_range_candidates:
                        current_combination += 1
                        logger.info(f"测试 {label} 参数组合 {current_combination}/{total_combinations}: "
                                  f"conv={conv_days}, stab={stab_days}, range=({ir_lower}, {ir_upper})")
                        
                        # 更新参数
                        self.update_rtb_parameters(label, conv_days, stab_days, ir_lower, ir_upper)
                        
                        # 运行模拟
                        session_dir = self.run_simulation()
                        if not session_dir:
                            logger.error(f"模拟失败，跳过此参数组合")
                            continue
                        
                        # 评估表现
                        investments = self.load_investments(session_dir)
                        avg_roi, win_rate, count = self.evaluate_label_performance(investments, label)
                        
                        logger.info(f"  -> 平均ROI: {avg_roi:.4f}, 胜率: {win_rate:.3f}, 投资次数: {count}")
                        
                        # 更新最优参数
                        score = (avg_roi, win_rate)
                        if score > best_score:
                            best_score = score
                            best_params = {
                                'convergence_days': conv_days,
                                'stability_days': stab_days,
                                'invest_range_lower': ir_lower,
                                'invest_range_upper': ir_upper,
                                'avg_roi': avg_roi,
                                'win_rate': win_rate,
                                'investment_count': count
                            }
                            logger.info(f"  🎯 新的最优参数！ROI: {avg_roi:.4f}, 胜率: {win_rate:.3f}")
            
            if best_params:
                optimal_params[label] = best_params
                logger.info(f"✅ {label} 最优参数: {best_params}")
        
        # 保存结果
        self._save_results(optimal_params)
        
        # 恢复原始文件
        self.restore_original_file()
        
        return optimal_params
    
    def _save_results(self, optimal_params: Dict[str, Any]):
        """保存搜索结果"""
        latest_session = self._get_latest_session_dir()
        if latest_session:
            output_file = latest_session / 'optimal_parameters.json'
        else:
            output_file = self.tmp_dir / f'optimal_parameters_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        output_file.write_text(json.dumps(optimal_params, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.success(f"最优参数已保存到: {output_file}")
        
        # 打印结果摘要
        logger.info("\n" + "="*60)
        logger.info("🎯 RTB策略最优参数搜索结果")
        logger.info("="*60)
        for label, params in optimal_params.items():
            logger.info(f"{label}:")
            logger.info(f"  收敛期: {params['convergence_days']} 天")
            logger.info(f"  稳定期: {params['stability_days']} 天")
            logger.info(f"  买入区间: [{params['invest_range_lower']}, {params['invest_range_upper']}]")
            logger.info(f"  预期表现: ROI {params['avg_roi']:.4f}, 胜率 {params['win_rate']:.3f}")
            logger.info("")


def main():
    """主函数"""
    searcher = ParamGridSearch()
    try:
        optimal_params = searcher.search_optimal_params()
        return optimal_params
    except Exception as e:
        logger.error(f"参数搜索失败: {e}")
        searcher.restore_original_file()
        raise


if __name__ == '__main__':
    main()
