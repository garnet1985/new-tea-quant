#!/usr/bin/env python3
"""
诊断V18策略条件，分析为什么没有找到投资机会
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

from utils.db.db_manager import DatabaseManager
from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings

def debug_v18_conditions():
    """诊断V18策略条件"""
    print("🔍 诊断V18策略条件")
    print("=" * 60)
    
    # 初始化数据库管理器
    db_manager = DatabaseManager()
    
    # 创建策略实例
    strategy = ReverseTrendBet(db_manager, settings)
    
    # 获取股票列表（前10只）
    stock_list_table = db_manager.get_table_instance('stock_list')
    stock_list = stock_list_table.load_filtered_stock_list(order_by='id')[:10]
    
    print(f"📊 分析前10只股票的条件满足情况:")
    print(f"股票列表: {[s['id'] for s in stock_list]}")
    
    condition_stats = {
        'ma_convergence': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'ma20_slope': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'ma60_slope': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'volume_trend': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'amount_ratio': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'price_change_pct': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'close_to_ma20': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'duration_weeks': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'convergence_ratio': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'historical_percentile': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'oscillation_position': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'volume_confirmation': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'rsi_signal': {'pass': 0, 'fail': 0, 'fail_reasons': []},
        'financial_conditions': {'pass': 0, 'fail': 0, 'fail_reasons': []},
    }
    
    for stock in stock_list:
        print(f"\n🔍 分析股票: {stock['id']} - {stock['name']}")
        
        try:
            # 获取股票数据
            from app.data_loader import DataLoader
            loader = DataLoader()
            required_data = loader.prepare_data(stock, settings)
            weekly_klines = required_data.get('klines', {}).get('weekly', [])
            
            if not weekly_klines or len(weekly_klines) < 100:
                print(f"  ❌ 数据不足，跳过")
                continue
            
            # 获取当前K线
            current_kline = weekly_klines[-1]
            
            # 计算技术特征
            features = ReverseTrendBet._calculate_optimized_features(weekly_klines, stock['id'], None)
            if not features:
                print(f"  ❌ 无法计算特征，跳过")
                continue
            
            # 获取财务指标
            financial_indicators = ReverseTrendBet._get_financial_indicators_from_klines(current_kline)
            
            print(f"  📊 技术特征:")
            print(f"    MA收敛度: {features['ma_convergence']:.4f} (阈值: <0.15)")
            print(f"    MA20斜率: {features['ma20_slope']:.4f} (阈值: >-0.05)")
            print(f"    MA60斜率: {features['ma60_slope']:.4f} (阈值: >-0.05)")
            print(f"    成交量趋势: {features['volume_trend']:.3f} (阈值: >-0.3)")
            print(f"    成交金额比率: {features['amount_ratio']:.3f} (阈值: >0.7)")
            print(f"    历史分位数: {features['historical_percentile']:.3f} (阈值: <0.4)")
            print(f"    成交量确认: {features['volume_confirmation']:.3f} (阈值: >0.7)")
            print(f"    RSI信号: {features['rsi_signal']:.1f} (阈值: <70)")
            
            print(f"  💰 财务指标:")
            print(f"    市值: {financial_indicators.get('market_cap', 0):.0f}万 (阈值: >300000)")
            print(f"    PE: {financial_indicators.get('pe_ratio', 0):.1f} (阈值: 15-150)")
            print(f"    PB: {financial_indicators.get('pb_ratio', 0):.2f} (阈值: 0.3-8)")
            print(f"    PS: {financial_indicators.get('ps_ratio', 0):.2f} (阈值: 0.5-15)")
            
            # 检查每个条件
            conditions = [
                ('ma_convergence', features['ma_convergence'] < 0.15),
                ('ma20_slope', features['ma20_slope'] > -0.05),
                ('ma60_slope', features['ma60_slope'] > -0.05),
                ('volume_trend', features['volume_trend'] > -0.3),
                ('amount_ratio', features['amount_ratio'] > 0.7),
                ('price_change_pct', features['price_change_pct'] > -6.0),
                ('close_to_ma20', features['close_to_ma20'] > -5.0),
                ('duration_weeks', features['duration_weeks'] < 20),
                ('convergence_ratio', features['convergence_ratio'] > 0.06),
                ('historical_percentile', features['historical_percentile'] < 0.4),
                ('oscillation_position', features['oscillation_position'] < 0.5),
                ('volume_confirmation', features['volume_confirmation'] > 0.7),
                ('rsi_signal', features['rsi_signal'] < 70),
            ]
            
            # 检查财务条件
            financial_pass = ReverseTrendBet._check_financial_conditions(financial_indicators)
            conditions.append(('financial_conditions', financial_pass))
            
            # 统计条件通过情况
            for condition_name, condition_result in conditions:
                if condition_result:
                    condition_stats[condition_name]['pass'] += 1
                else:
                    condition_stats[condition_name]['fail'] += 1
                    if condition_name == 'ma_convergence':
                        condition_stats[condition_name]['fail_reasons'].append(f"{stock['id']}: {features['ma_convergence']:.4f}")
                    elif condition_name == 'financial_conditions':
                        condition_stats[condition_name]['fail_reasons'].append(f"{stock['id']}: 财务筛选失败")
            
            # 显示通过的条件
            passed_conditions = [name for name, result in conditions if result]
            failed_conditions = [name for name, result in conditions if not result]
            
            print(f"  ✅ 通过条件: {len(passed_conditions)}/{len(conditions)}")
            if failed_conditions:
                print(f"  ❌ 失败条件: {', '.join(failed_conditions[:5])}")  # 只显示前5个
            
        except Exception as e:
            print(f"  ❌ 分析失败: {e}")
    
    # 显示统计结果
    print(f"\n📊 条件通过率统计 (基于{len(stock_list)}只股票):")
    print("=" * 60)
    
    for condition_name, stats in condition_stats.items():
        total = stats['pass'] + stats['fail']
        if total > 0:
            pass_rate = stats['pass'] / total * 100
            print(f"{condition_name:20s}: {pass_rate:5.1f}% ({stats['pass']}/{total})")
            
            # 显示一些失败原因
            if stats['fail_reasons'] and len(stats['fail_reasons']) <= 3:
                for reason in stats['fail_reasons']:
                    print(f"  └─ {reason}")
    
    print(f"\n🎯 诊断建议:")
    
    # 找出通过率最低的条件
    pass_rates = []
    for condition_name, stats in condition_stats.items():
        total = stats['pass'] + stats['fail']
        if total > 0:
            pass_rate = stats['pass'] / total * 100
            pass_rates.append((condition_name, pass_rate))
    
    pass_rates.sort(key=lambda x: x[1])
    
    print(f"通过率最低的条件:")
    for condition_name, pass_rate in pass_rates[:5]:
        print(f"  - {condition_name}: {pass_rate:.1f}%")
    
    print(f"\n建议:")
    print(f"1. 考虑进一步放宽通过率低于20%的条件")
    print(f"2. 特别关注财务筛选条件是否过于严格")
    print(f"3. 检查数据质量，确保财务指标数据完整")

if __name__ == "__main__":
    debug_v18_conditions()
