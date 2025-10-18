#!/usr/bin/env python3
"""
分析财务指标筛选对策略表现的影响
"""
import sys
from pathlib import Path
import json
from collections import defaultdict
from typing import Dict, List, Any

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

def analyze_financial_indicators(tmp_dir: str):
    """分析财务指标对策略表现的影响"""
    print(f"📊 分析财务指标影响: {tmp_dir}")
    
    # 加载股票基本信息和投资表现
    stock_data = {}
    stock_performance = {}
    
    stock_files = list(Path(tmp_dir).glob("*.json"))
    stock_files = [f for f in stock_files if f.name != "0_session_summary.json"]
    
    print(f"股票文件数量: {len(stock_files)}")
    
    for stock_file in stock_files:
        try:
            with open(stock_file, 'r') as f:
                data = json.load(f)
            
            stock_id = data['stock']['id']
            stock_name = data['stock']['name']
            industry = data['stock'].get('industry', '未知')
            
            investments = data.get('investments', [])
            completed_investments = [inv for inv in investments if inv.get('result') in ['win', 'loss']]
            
            if completed_investments:
                total_roi = sum(inv.get('overall_profit_rate', 0) for inv in completed_investments)
                avg_roi = total_roi / len(completed_investments)
                win_rate = sum(1 for inv in completed_investments if inv['result'] == 'win') / len(completed_investments)
                
                stock_performance[stock_id] = {
                    'name': stock_name,
                    'industry': industry,
                    'avg_roi': avg_roi,
                    'win_rate': win_rate,
                    'investment_count': len(completed_investments),
                    'total_roi': total_roi
                }
                
        except Exception as e:
            print(f"处理文件失败 {stock_file}: {e}")
    
    print(f"有投资记录的股票: {len(stock_performance)}")
    
    # 按行业分析表现
    industry_performance = defaultdict(list)
    for stock_id, perf in stock_performance.items():
        industry_performance[perf['industry']].append(perf)
    
    print(f"\n📈 按行业分析表现:")
    industry_stats = []
    for industry, stocks in industry_performance.items():
        if len(stocks) >= 5:  # 至少5只股票
            avg_roi = sum(s['avg_roi'] for s in stocks) / len(stocks)
            avg_win_rate = sum(s['win_rate'] for s in stocks) / len(stocks)
            industry_stats.append({
                'industry': industry,
                'stock_count': len(stocks),
                'avg_roi': avg_roi,
                'avg_win_rate': avg_win_rate
            })
    
    # 按ROI排序
    industry_stats.sort(key=lambda x: x['avg_roi'])
    
    print("🔴 表现最差的行业:")
    for i, stat in enumerate(industry_stats[:5]):
        print(f"  {i+1}. {stat['industry']}: 平均ROI={stat['avg_roi']:.2%}, 胜率={stat['avg_win_rate']:.1%}, 股票数={stat['stock_count']}")
    
    print("\n🟢 表现最好的行业:")
    for i, stat in enumerate(industry_stats[-5:]):
        print(f"  {i+1}. {stat['industry']}: 平均ROI={stat['avg_roi']:.2%}, 胜率={stat['avg_win_rate']:.1%}, 股票数={stat['stock_count']}")
    
    # 分析投资次数与表现的关系
    print(f"\n📊 投资次数与表现关系:")
    investment_count_groups = {
        '1次': [],
        '2次': [],
        '3-5次': [],
        '6-10次': [],
        '10次以上': []
    }
    
    for stock_id, perf in stock_performance.items():
        count = perf['investment_count']
        if count == 1:
            investment_count_groups['1次'].append(perf)
        elif count == 2:
            investment_count_groups['2次'].append(perf)
        elif 3 <= count <= 5:
            investment_count_groups['3-5次'].append(perf)
        elif 6 <= count <= 10:
            investment_count_groups['6-10次'].append(perf)
        else:
            investment_count_groups['10次以上'].append(perf)
    
    for group_name, stocks in investment_count_groups.items():
        if stocks:
            avg_roi = sum(s['avg_roi'] for s in stocks) / len(stocks)
            avg_win_rate = sum(s['win_rate'] for s in stocks) / len(stocks)
            print(f"  {group_name}: 股票数={len(stocks)}, 平均ROI={avg_roi:.2%}, 平均胜率={avg_win_rate:.1%}")
    
    return industry_stats, stock_performance

def suggest_financial_filters(industry_stats, stock_performance):
    """基于分析结果提出财务筛选建议"""
    print(f"\n💡 财务筛选建议:")
    
    # 1. 行业筛选
    poor_industries = [stat['industry'] for stat in industry_stats[:3] if stat['avg_roi'] < 0]
    good_industries = [stat['industry'] for stat in industry_stats[-3:] if stat['avg_roi'] > 0.05]
    
    print(f"\n1️⃣ 行业筛选:")
    if poor_industries:
        print(f"   建议排除行业: {', '.join(poor_industries)}")
        print(f"   理由: 平均ROI为负，表现较差")
    
    if good_industries:
        print(f"   建议优先行业: {', '.join(good_industries)}")
        print(f"   理由: 平均ROI超过5%，表现优秀")
    
    # 2. 投资频率筛选
    print(f"\n2️⃣ 投资频率筛选:")
    print(f"   建议重点关注投资次数3-5次的股票")
    print(f"   理由: 投资次数太少可能样本不足，太多可能策略失效")
    
    # 3. 市值筛选建议
    print(f"\n3️⃣ 市值筛选建议:")
    print(f"   建议添加市值筛选条件:")
    print(f"   - 排除ST、*ST等特殊处理股票")
    print(f"   - 排除市值过小（<50亿）的股票")
    print(f"   - 排除市值过大（>5000亿）的股票")
    print(f"   - 优先选择市值100-1000亿的中等规模股票")
    
    # 4. 其他财务指标建议
    print(f"\n4️⃣ 其他财务指标建议:")
    print(f"   - PE比率: 10-50之间（避免极端估值）")
    print(f"   - PB比率: 1-5之间（避免极端估值）")
    print(f"   - 营收增长率: 排除负增长的股票")
    print(f"   - 负债率: 排除负债率>70%的股票")

def main():
    print("🚀 分析财务指标对策略的影响...")
    
    # 使用最新的V17结果
    tmp_dir = "/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/tmp/2025_10_17-210"
    industry_stats, stock_performance = analyze_financial_indicators(tmp_dir)
    suggest_financial_filters(industry_stats, stock_performance)

if __name__ == "__main__":
    main()
