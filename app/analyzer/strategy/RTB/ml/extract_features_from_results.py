#!/usr/bin/env python3
"""
从现有的RTB模拟结果中提取特征快照数据
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))

def extract_features_from_simulation_results(results_dir: str) -> List[Dict[str, Any]]:
    """从模拟结果目录中提取特征快照"""
    results_path = Path(results_dir)
    snapshots = []
    
    # 读取会话摘要
    summary_file = results_path / "0_session_summary.json"
    if summary_file.exists():
        with open(summary_file, 'r', encoding='utf-8') as f:
            session_summary = json.load(f)
        print(f"📊 会话摘要: {session_summary.get('total_investments', 0)} 次投资")
    
    # 遍历所有股票结果文件
    for stock_file in results_path.glob("*.json"):
        if stock_file.name == "0_session_summary.json":
            continue
            
        try:
            with open(stock_file, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
            
            stock_id = stock_data.get('stock', {}).get('id', stock_file.stem)
            stock_name = stock_data.get('stock', {}).get('name', '')
            
            # 处理每笔投资
            investments = stock_data.get('investments', [])
            for investment in investments:
                # 提取特征
                features = investment.get('extra_fields', {}).get('features', {})
                labels = investment.get('extra_fields', {}).get('labels', {})
                
                # 提取投资结果
                roi = investment.get('overall_profit_rate', 0)
                duration_days = investment.get('duration_in_days', 0)
                
                # 计算最大回撤
                max_drawdown = 0.0
                tracking = investment.get('tracking', {})
                if tracking.get('min_close_reached', {}).get('ratio'):
                    max_drawdown = abs(tracking['min_close_reached']['ratio'])
                
                # 创建快照记录
                snapshot = {
                    'stock_id': stock_id,
                    'stock_name': stock_name,
                    'investment_date': investment.get('start_date', ''),
                    'settlement_date': investment.get('end_date', ''),
                    'features': features,
                    'labels': labels,
                    'has_investment_result': True,
                    'investment_result': {
                        'roi': roi,
                        'duration_days': duration_days,
                        'max_drawdown': max_drawdown,
                        'result': investment.get('result', ''),
                        'purchase_price': investment.get('purchase_price', 0),
                        'overall_profit': investment.get('overall_profit', 0)
                    },
                    'opportunity_metadata': {
                        'strategy_version': 'V16_ML_Optimized',
                        'investment_id': f"{stock_id}_{investment.get('start_date', '')}"
                    }
                }
                
                snapshots.append(snapshot)
                
        except Exception as e:
            print(f"❌ 处理文件 {stock_file.name} 时出错: {e}")
            continue
    
    print(f"✅ 成功提取 {len(snapshots)} 个特征快照")
    return snapshots

def save_extracted_snapshots(snapshots: List[Dict[str, Any]], output_dir: str):
    """保存提取的特征快照"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 保存JSON格式
    json_file = output_path / "feature_snapshots.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(snapshots, f, ensure_ascii=False, indent=2)
    
    print(f"💾 特征快照已保存到: {json_file}")
    
    # 保存CSV格式（简化版本）
    try:
        import pandas as pd
        
        # 展平数据结构
        flattened_data = []
        for snapshot in snapshots:
            row = {
                'stock_id': snapshot['stock_id'],
                'stock_name': snapshot['stock_name'],
                'investment_date': snapshot['investment_date'],
                'roi': snapshot['investment_result']['roi'],
                'duration_days': snapshot['investment_result']['duration_days'],
                'max_drawdown': snapshot['investment_result']['max_drawdown'],
                'result': snapshot['investment_result']['result']
            }
            
            # 添加特征
            features = snapshot.get('features', {})
            for key, value in features.items():
                row[f'feature_{key}'] = value
            
            # 添加标签
            labels = snapshot.get('labels', {})
            for key, value in labels.items():
                row[f'label_{key}'] = value
            
            flattened_data.append(row)
        
        df = pd.DataFrame(flattened_data)
        csv_file = output_path / "feature_snapshots.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"📊 CSV文件已保存到: {csv_file}")
        
    except ImportError:
        print("⚠️ pandas未安装，跳过CSV导出")

def main():
    """主函数"""
    # 使用现有的245版本结果
    results_dir = "app/analyzer/strategy/RTB/tmp/2025_10_20-245"
    output_dir = "app/analyzer/strategy/RTB/tmp/2025_10_20-extracted_features"
    
    print(f"🔍 从 {results_dir} 提取特征快照...")
    
    # 提取特征快照
    snapshots = extract_features_from_simulation_results(results_dir)
    
    if snapshots:
        # 保存快照
        save_extracted_snapshots(snapshots, output_dir)
        
        # 显示统计信息
        print(f"\n📈 提取统计:")
        print(f"  总快照数: {len(snapshots)}")
        
        # 按市值标签统计
        market_cap_stats = {}
        for snapshot in snapshots:
            labels = snapshot.get('labels', {})
            market_cap = labels.get('market_cap', 'unknown')
            
            # 处理market_cap可能是list的情况
            if isinstance(market_cap, list):
                market_cap = market_cap[0] if market_cap else 'unknown'
            
            if market_cap not in market_cap_stats:
                market_cap_stats[market_cap] = {'count': 0, 'total_roi': 0}
            market_cap_stats[market_cap]['count'] += 1
            market_cap_stats[market_cap]['total_roi'] += snapshot['investment_result']['roi']
        
        print(f"  市值分布:")
        for market_cap, stats in market_cap_stats.items():
            avg_roi = stats['total_roi'] / stats['count'] if stats['count'] > 0 else 0
            print(f"    {market_cap}: {stats['count']} 次, 平均ROI: {avg_roi:.4f}")
        
        print(f"\n🎯 现在可以使用离线优化器分析这些特征快照！")
        print(f"  运行: python app/analyzer/strategy/RTB/ml/offline_optimizer.py {output_dir}/feature_snapshots.json")
        
    else:
        print("❌ 没有提取到任何特征快照")

if __name__ == "__main__":
    main()
