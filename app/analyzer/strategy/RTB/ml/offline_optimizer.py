#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RTB策略离线优化器

基于特征快照进行参数和止损止盈策略的离线优化
支持市值分层优化
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from loguru import logger


class RTBOfflineOptimizer:
    """RTB策略离线优化器"""
    
    def __init__(self, snapshots_file: Path):
        """
        初始化优化器
        
        Args:
            snapshots_file: 特征快照文件路径
        """
        self.snapshots_file = snapshots_file
        self.snapshots = self._load_snapshots()
        self.df = self._prepare_dataframe()
        
    def _load_snapshots(self) -> List[Dict[str, Any]]:
        """加载特征快照"""
        try:
            with open(self.snapshots_file, 'r', encoding='utf-8') as f:
                snapshots = json.load(f)
            logger.info(f"已加载 {len(snapshots)} 个特征快照")
            return snapshots
        except Exception as e:
            logger.error(f"加载快照失败: {e}")
            return []
    
    def _prepare_dataframe(self) -> pd.DataFrame:
        """准备分析用的DataFrame"""
        if not self.snapshots:
            return pd.DataFrame()
        
        # 提取数据
        data = []
        for snapshot in self.snapshots:
            row = {
                'stock_id': snapshot['stock_id'],
                'date': snapshot.get('investment_date', ''),  # 使用investment_date而不是date
                'roi': snapshot.get('investment_result', {}).get('roi', None),
                'duration_days': snapshot.get('investment_result', {}).get('duration_days', None),
                'max_drawdown': snapshot.get('investment_result', {}).get('max_drawdown', None),
                'has_investment_result': snapshot.get('has_investment_result', False)
            }
            
            # 添加特征
            features = snapshot.get('features', {})
            for key, value in features.items():
                row[f'feature_{key}'] = value
            
            # 添加标签
            labels = snapshot.get('labels', {})
            for key, value in labels.items():
                # 处理value可能是list的情况
                if isinstance(value, list):
                    row[f'label_{key}'] = value[0] if value else None
                else:
                    row[f'label_{key}'] = value
            
            # 添加元数据
            metadata = snapshot.get('opportunity_metadata', {})
            for key, value in metadata.items():
                row[f'metadata_{key}'] = value
            
            data.append(row)
        
        df = pd.DataFrame(data)
        logger.info(f"准备DataFrame: {len(df)} 行, {len(df.columns)} 列")
        return df
    
    def analyze_market_cap_performance(self) -> Dict[str, Dict[str, float]]:
        """分析不同市值标签的表现"""
        if self.df.empty:
            return {}
        
        # 筛选有投资结果的记录
        df_with_results = self.df[self.df['has_investment_result'] == True].copy()
        
        if df_with_results.empty:
            logger.warning("没有投资结果数据可供分析")
            return {}
        
        # 分析市值标签表现
        market_cap_col = 'label_market_cap'
        if market_cap_col not in df_with_results.columns:
            logger.warning(f"没有找到市值标签列: {market_cap_col}")
            return {}
        
        market_cap_labels = ['large_cap', 'mid_cap', 'small_cap']
        results = {}
        
        for label in market_cap_labels:
            # 筛选该标签的投资
            label_df = df_with_results[df_with_results[market_cap_col] == label].copy()
            
            if len(label_df) == 0:
                continue
            
            # 计算统计指标
            roi_values = label_df['roi'].dropna()
            duration_values = label_df['duration_days'].dropna()
            drawdown_values = label_df['max_drawdown'].dropna()
            
            results[label] = {
                'count': len(label_df),
                'avg_roi': roi_values.mean() if len(roi_values) > 0 else 0.0,
                'median_roi': roi_values.median() if len(roi_values) > 0 else 0.0,
                'win_rate': (roi_values > 0).mean() if len(roi_values) > 0 else 0.0,
                'avg_duration_days': duration_values.mean() if len(duration_values) > 0 else 0.0,
                'avg_max_drawdown': drawdown_values.mean() if len(drawdown_values) > 0 else 0.0,
                'std_roi': roi_values.std() if len(roi_values) > 0 else 0.0
            }
        
        return results
    
    def optimize_parameters_by_market_cap(self, 
                                        optimization_target: str = 'roi',
                                        grid_size: str = 'small') -> Dict[str, Dict[str, Any]]:
        """
        按市值标签优化参数
        
        Args:
            optimization_target: 优化目标 ('roi', 'win_rate', 'sharpe')
            grid_size: 网格大小 ('small', 'medium', 'large')
        
        Returns:
            各市值标签的最优参数
        """
        if self.df.empty:
            return {}
        
        # 定义参数网格
        if grid_size == 'small':
            convergence_days_candidates = [15, 20, 25]
            stability_days_candidates = [8, 10, 12]
            invest_range_candidates = [0.008, 0.01, 0.012]
            stop_loss_candidates = [0.12, 0.15, 0.18]
            take_profit_candidates = [0.15, 0.20, 0.25]
        elif grid_size == 'medium':
            convergence_days_candidates = [15, 18, 20, 22, 25, 30]
            stability_days_candidates = [6, 8, 10, 12, 15]
            invest_range_candidates = [0.006, 0.008, 0.01, 0.012, 0.015]
            stop_loss_candidates = [0.10, 0.12, 0.15, 0.18, 0.20]
            take_profit_candidates = [0.15, 0.18, 0.20, 0.25, 0.30]
        else:  # large
            convergence_days_candidates = list(range(10, 35, 2))
            stability_days_candidates = list(range(5, 20, 1))
            invest_range_candidates = [0.005, 0.006, 0.008, 0.01, 0.012, 0.015, 0.018, 0.02]
            stop_loss_candidates = [0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.22]
            take_profit_candidates = [0.12, 0.15, 0.18, 0.20, 0.25, 0.30, 0.35]
        
        market_cap_labels = ['large_cap', 'mid_cap', 'small_cap']
        optimal_params = {}
        
        for label in market_cap_labels:
            logger.info(f"开始优化 {label} 参数...")
            
            best_score = -float('inf')
            best_params = None
            total_combinations = (len(convergence_days_candidates) * 
                                len(stability_days_candidates) * 
                                len(invest_range_candidates) * 
                                len(stop_loss_candidates) * 
                                len(take_profit_candidates))
            
            current_combination = 0
            
            # 网格搜索
            for conv_days in convergence_days_candidates:
                for stab_days in stability_days_candidates:
                    for invest_range in invest_range_candidates:
                        for stop_loss in stop_loss_candidates:
                            for take_profit in take_profit_candidates:
                                current_combination += 1
                                
                                if current_combination % 100 == 0:
                                    logger.info(f"  {label} 进度: {current_combination}/{total_combinations}")
                                
                                # 评估参数组合
                                score = self._evaluate_parameter_combination(
                                    label, conv_days, stab_days, invest_range, 
                                    stop_loss, take_profit, optimization_target
                                )
                                
                                if score > best_score:
                                    best_score = score
                                    best_params = {
                                        'convergence_days': conv_days,
                                        'stability_days': stab_days,
                                        'invest_range_lower': invest_range,
                                        'invest_range_upper': invest_range,
                                        'stop_loss_ratio': stop_loss,
                                        'take_profit_ratio': take_profit,
                                        'score': score
                                    }
            
            if best_params:
                optimal_params[label] = best_params
                logger.info(f"{label} 最优参数: {best_params}")
        
        return optimal_params
    
    def _evaluate_parameter_combination(self, 
                                      label: str,
                                      conv_days: int,
                                      stab_days: int,
                                      invest_range: float,
                                      stop_loss: float,
                                      take_profit: float,
                                      optimization_target: str) -> float:
        """
        评估参数组合的表现
        
        这里使用简化的评估方法，实际应用中可以使用更复杂的模拟
        """
        # 筛选该标签的数据
        label_col = f'label_{label}'
        if label_col not in self.df.columns:
            return 0.0
        
        label_df = self.df[self.df[label_col].notna()].copy()
        if label_df.empty:
            return 0.0
        
        # 筛选有投资结果的记录
        df_with_results = label_df[label_df['has_investment_result'] == True].copy()
        if df_with_results.empty:
            return 0.0
        
        # 基于参数调整模拟投资结果
        simulated_rois = []
        simulated_durations = []
        
        for _, row in df_with_results.iterrows():
            # 基于参数调整ROI（简化模型）
            base_roi = row['roi'] if pd.notna(row['roi']) else 0.0
            base_duration = row['duration_days'] if pd.notna(row['duration_days']) else 100
            
            # 参数影响模拟
            conv_factor = 1.0 + (conv_days - 20) * 0.01  # 收敛期影响
            stab_factor = 1.0 + (stab_days - 10) * 0.005  # 稳定期影响
            range_factor = 1.0 + (invest_range - 0.01) * 10  # 买入区间影响
            
            # 止损止盈影响
            stop_loss_factor = 1.0 + (0.15 - stop_loss) * 2  # 更严格的止损可能提高胜率
            take_profit_factor = 1.0 + (take_profit - 0.20) * 0.5  # 适中的止盈
            
            # 综合调整
            adjusted_roi = base_roi * conv_factor * stab_factor * range_factor * stop_loss_factor * take_profit_factor
            adjusted_duration = base_duration * (1.0 + (conv_days - 20) * 0.02)
            
            simulated_rois.append(adjusted_roi)
            simulated_durations.append(adjusted_duration)
        
        # 计算优化目标
        if optimization_target == 'roi':
            return np.mean(simulated_rois) if simulated_rois else 0.0
        elif optimization_target == 'win_rate':
            win_count = sum(1 for roi in simulated_rois if roi > 0)
            return win_count / len(simulated_rois) if simulated_rois else 0.0
        elif optimization_target == 'sharpe':
            if not simulated_rois:
                return 0.0
            mean_roi = np.mean(simulated_rois)
            std_roi = np.std(simulated_rois)
            return mean_roi / std_roi if std_roi > 0 else 0.0
        else:
            return 0.0
    
    def generate_optimization_report(self, output_dir: Path = None):
        """生成优化报告"""
        if output_dir is None:
            output_dir = self.snapshots_file.parent / "optimization_report"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 分析市值表现
        market_cap_performance = self.analyze_market_cap_performance()
        
        # 生成参数优化建议
        optimal_params = self.optimize_parameters_by_market_cap()
        
        # 保存报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'market_cap_performance': market_cap_performance,
            'optimal_parameters': optimal_params,
            'summary': {
                'total_snapshots': len(self.snapshots),
                'total_investments': len(self.df[self.df.get('has_investment_result', False) == True]) if not self.df.empty else 0,
                'market_cap_coverage': len(market_cap_performance)
            }
        }
        
        report_file = output_dir / "optimization_report.json"
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        
        logger.info(f"优化报告已保存到: {report_file}")
        return report


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python offline_optimizer.py <snapshots_file_path>")
        print("示例: python offline_optimizer.py app/analyzer/strategy/RTB/tmp/2025_10_20-extracted_features/feature_snapshots.json")
        sys.exit(1)
    
    snapshots_file = Path(sys.argv[1])
    
    if snapshots_file.exists():
        logger.info(f"🔍 开始分析特征快照: {snapshots_file}")
        optimizer = RTBOfflineOptimizer(snapshots_file)
        
        # 分析市值表现
        market_cap_performance = optimizer.analyze_market_cap_performance()
        logger.info("📊 市值表现分析:")
        for label, performance in market_cap_performance.items():
            logger.info(f"  {label}: ROI={performance['avg_roi']:.4f}, 胜率={performance['win_rate']:.3f}, 次数={performance['count']}")
        
        # 生成优化报告
        optimization_report = optimizer.generate_optimization_report()
        logger.info("✅ 优化报告已生成")
        
        # 显示报告摘要
        summary = optimization_report.get('summary', {})
        logger.info(f"📈 总快照数: {summary.get('total_snapshots', 0)}")
        logger.info(f"📊 总投资数: {summary.get('total_investments', 0)}")
        logger.info(f"🏷️ 市值覆盖: {summary.get('market_cap_coverage', 0)}")
        
        # 显示最优参数建议
        optimal_params = optimization_report.get('optimal_parameters', {})
        if optimal_params:
            logger.info("🎯 最优参数建议:")
            for label, params in optimal_params.items():
                logger.info(f"  {label}:")
                logger.info(f"    收敛期: {params['convergence_days']} 天")
                logger.info(f"    稳定期: {params['stability_days']} 天")
                logger.info(f"    买入区间: [{params['invest_range_lower']}, {params['invest_range_upper']}]")
                logger.info(f"    止损: {params['stop_loss_ratio']:.2%}")
                logger.info(f"    止盈: {params['take_profit_ratio']:.2%}")
                logger.info(f"    评分: {params['score']:.4f}")
        
    else:
        logger.error(f"快照文件不存在: {snapshots_file}")


if __name__ == '__main__':
    main()
