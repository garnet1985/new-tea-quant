#!/usr/bin/env python3
"""
分析黑名单候选股票
"""
import sys
from pathlib import Path
import json
from collections import defaultdict
from typing import Dict, List, Any

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

def analyze_stock_performance(tmp_dir: str):
    """分析股票表现，找出黑名单候选"""
    print(f"📊 分析股票表现: {tmp_dir}")
    
    stock_performance = defaultdict(list)
    stock_summary = defaultdict(lambda: {
        'total_investments': 0,
        'successful_investments': 0,
        'failed_investments': 0,
        'total_roi': 0.0,
        'avg_roi': 0.0,
        'win_rate': 0.0,
        'worst_roi': float('inf'),
        'best_roi': float('-inf')
    })
    
    # 加载所有股票文件
    stock_files = list(Path(tmp_dir).glob("*.json"))
    stock_files = [f for f in stock_files if f.name != "0_session_summary.json"]
    
    print(f"股票文件数量: {len(stock_files)}")
    
    for stock_file in stock_files:
        try:
            with open(stock_file, 'r') as f:
                stock_data = json.load(f)
            
            stock_id = stock_data['stock']['id']
            stock_name = stock_data['stock']['name']
            investments = stock_data.get('investments', [])
            
            for inv in investments:
                if inv.get('result') in ['win', 'loss']:
                    roi = inv.get('overall_profit_rate', 0)
                    stock_performance[stock_id].append({
                        'roi': roi,
                        'result': inv['result'],
                        'duration': inv.get('duration_in_days', 0)
                    })
                    
                    # 更新汇总
                    summary = stock_summary[stock_id]
                    summary['total_investments'] += 1
                    summary['total_roi'] += roi
                    
                    if inv['result'] == 'win':
                        summary['successful_investments'] += 1
                    else:
                        summary['failed_investments'] += 1
                    
                    summary['worst_roi'] = min(summary['worst_roi'], roi)
                    summary['best_roi'] = max(summary['best_roi'], roi)
            
            # 计算平均值
            if stock_summary[stock_id]['total_investments'] > 0:
                summary = stock_summary[stock_id]
                summary['avg_roi'] = summary['total_roi'] / summary['total_investments']
                summary['win_rate'] = summary['successful_investments'] / summary['total_investments']
                
        except Exception as e:
            print(f"处理文件失败 {stock_file}: {e}")
    
    # 分析结果
    print(f"\n📈 股票表现分析 (共{len(stock_summary)}只股票):")
    
    # 统计投资次数分布
    investment_counts = [summary['total_investments'] for summary in stock_summary.values()]
    avg_investments = sum(investment_counts) / len(investment_counts) if investment_counts else 0
    print(f"平均每只股票投资次数: {avg_investments:.1f}")
    print(f"投资次数≥3的股票: {sum(1 for c in investment_counts if c >= 3)}")
    print(f"投资次数≥5的股票: {sum(1 for c in investment_counts if c >= 5)}")
    
    # 找出表现最差的股票
    worst_stocks = []
    best_stocks = []
    
    for stock_id, summary in stock_summary.items():
        if summary['total_investments'] >= 3:  # 至少3次投资
            if summary['avg_roi'] < -0.05:  # 平均ROI低于-5% (小数形式)
                worst_stocks.append((stock_id, summary))
            elif summary['avg_roi'] > 0.15:  # 平均ROI高于15% (小数形式)
                best_stocks.append((stock_id, summary))
    
    # 显示ROI分布
    rois = [summary['avg_roi'] for summary in stock_summary.values() if summary['total_investments'] >= 3]
    if rois:
        print(f"ROI分布 (投资次数≥3):")
        print(f"  最低ROI: {min(rois):.2%}")
        print(f"  最高ROI: {max(rois):.2%}")
        print(f"  平均ROI: {sum(rois)/len(rois):.2%}")
        print(f"  负ROI股票数: {sum(1 for r in rois if r < 0)}")
        print(f"  ROI<-5%股票数: {sum(1 for r in rois if r < -0.05)}")
    
    # 排序
    worst_stocks.sort(key=lambda x: x[1]['avg_roi'])
    best_stocks.sort(key=lambda x: x[1]['avg_roi'], reverse=True)
    
    print(f"\n🔴 表现最差的股票 (平均ROI < -5%):")
    for i, (stock_id, summary) in enumerate(worst_stocks[:10]):
        print(f"  {i+1}. {stock_id}: 平均ROI={summary['avg_roi']:.2%}, 胜率={summary['win_rate']:.1%}, 投资次数={summary['total_investments']}")
    
    print(f"\n🟢 表现最好的股票 (平均ROI > 15%):")
    for i, (stock_id, summary) in enumerate(best_stocks[:10]):
        print(f"  {i+1}. {stock_id}: 平均ROI={summary['avg_roi']:.2%}, 胜率={summary['win_rate']:.1%}, 投资次数={summary['total_investments']}")
    
    # 生成黑名单建议
    blacklist_candidates = [stock_id for stock_id, summary in worst_stocks if summary['total_investments'] >= 3]
    
    print(f"\n🚫 黑名单建议 (投资次数≥3且平均ROI<-5%):")
    print(f"候选股票数量: {len(blacklist_candidates)}")
    for stock_id in blacklist_candidates[:20]:  # 显示前20个
        summary = stock_summary[stock_id]
        print(f"  {stock_id}: 平均ROI={summary['avg_roi']:.2%}, 胜率={summary['win_rate']:.1%}, 投资次数={summary['total_investments']}")
    
    return blacklist_candidates, stock_summary

def main():
    print("🚀 分析黑名单候选股票...")
    
    # 使用最新的V17结果
    tmp_dir = "/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/tmp/2025_10_17-210"
    blacklist_candidates, stock_summary = analyze_stock_performance(tmp_dir)
    
    print(f"\n💡 建议:")
    print(f"1. 考虑将{len(blacklist_candidates)}只表现最差的股票加入黑名单")
    print(f"2. 这些股票平均ROI都低于-5%，胜率普遍较低")
    print(f"3. 剔除这些股票可能会显著提升整体策略表现")

if __name__ == "__main__":
    main()
