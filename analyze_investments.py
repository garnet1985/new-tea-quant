import json
import os

# 读取所有JSON文件
json_dir = 'app/analyzer/strategy/historicLow/tmp/2025_09_02-217'
stock_data = []

for filename in os.listdir(json_dir):
    if filename.endswith('.json') and filename != 'session_summary.json':
        filepath = os.path.join(json_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            stock_data.append(data)

# 分析每个股票的数据
print('📊 股票投资结果分析')
print('=' * 120)
print('股票代码    状态     投资价格    止盈价格    止损价格    实际收益    持有天数  最高价    最低价')
print('=' * 120)

for stock in stock_data:
    stock_info = stock['stock_info']
    result = stock['results'][0]
    
    code = stock_info['code']
    status = result['status']
    purchase_price = result['target']['purchase_price']
    win_price = result['target']['win_price']
    loss_price = result['target']['loss_price']
    profit_loss = result['settlement_info']['profit_loss']
    duration_days = result['settlement_info']['duration_days']
    max_close = result['settlement_info']['max_close']
    min_close = result['settlement_info']['min_close']
    
    print(f'{code:<10} {status:<8} {purchase_price:<10.4f} {win_price:<10.4f} {loss_price:<10.4f} {profit_loss:<10.4f} {duration_days:<8} {max_close:<10.4f} {min_close:<10.4f}')

print('\n📈 Freeze Data统计信息对比')
print('=' * 120)
print('股票代码    平均涨跌幅  标准差    价格区间  价格比值  区间/投资价比  上涨天数  下跌天数')
print('=' * 120)

for stock in stock_data:
    stock_info = stock['stock_info']
    result = stock['results'][0]
    freeze_stats = result['freeze_data_stats']
    
    code = stock_info['code']
    mean_change = freeze_stats['mean_change_rate']
    std_change = freeze_stats['std_change_rate']
    close_range = freeze_stats['close_range']
    close_ratio = freeze_stats['close_ratio']
    range_to_invest = freeze_stats['range_to_invest_ratio']
    positive_days = freeze_stats['positive_days']
    negative_days = freeze_stats['negative_days']
    
    print(f'{code:<10} {mean_change*100:<12.2f}% {std_change*100:<10.2f}% {close_range:<10.4f} {close_ratio:<10.4f} {range_to_invest*100:<12.2f}% {positive_days:<8} {negative_days:<8}')

print('\n🎯 重点分析你提到的4个股票:')
print('=' * 80)

problem_stocks = ['000690', '000692', '000750', '000712']
for stock in stock_data:
    stock_info = stock['stock_info']
    if stock_info['code'] in problem_stocks:
        result = stock['results'][0]
        freeze_stats = result['freeze_data_stats']
        
        print(f'\n{stock_info["code"]} - {stock_info["name"]} ({result["status"]})')
        print(f'  投资价格: {result["target"]["purchase_price"]:.4f}')
        print(f'  止盈价格: {result["target"]["win_price"]:.4f} (需要上涨{result["target"]["stop_win_rate"]*100:.1f}%)')
        print(f'  止损价格: {result["target"]["loss_price"]:.4f} (下跌{result["target"]["stop_loss_rate"]*100:.1f}%)')
        print(f'  实际收益: {result["settlement_info"]["profit_loss"]:.4f}')
        print(f'  持有期间最高: {result["settlement_info"]["max_close"]:.4f} (涨幅{result["settlement_info"]["max_close_rate"]*100:.1f}%)')
        print(f'  持有期间最低: {result["settlement_info"]["min_close"]:.4f} (跌幅{result["settlement_info"]["min_close_rate"]*100:.1f}%)')
        print(f'  Freeze期间价格区间: {freeze_stats["close_range"]:.4f} (比值{freeze_stats["close_ratio"]:.4f})')
        print(f'  区间/投资价比: {freeze_stats["range_to_invest_ratio"]*100:.1f}%')
        print(f'  平均涨跌幅: {freeze_stats["mean_change_rate"]*100:.2f}%')
        print(f'  涨跌幅标准差: {freeze_stats["std_change_rate"]*100:.2f}%')

print('\n🔍 规律分析:')
print('=' * 50)

# 分析波动不够的股票
print('\n1. 波动不够导致投资失败的股票:')
low_volatility_stocks = []
for stock in stock_data:
    stock_info = stock['stock_info']
    result = stock['results'][0]
    freeze_stats = result['freeze_data_stats']
    
    # 判断波动是否足够
    close_ratio = freeze_stats['close_ratio']
    range_to_invest = freeze_stats['range_to_invest_ratio']
    
    # 如果价格比值小于1.3且区间/投资价比小于30%，认为波动不够
    if close_ratio < 1.3 and range_to_invest < 0.3:
        low_volatility_stocks.append({
            'code': stock_info['code'],
            'name': stock_info['name'],
            'status': result['status'],
            'close_ratio': close_ratio,
            'range_to_invest': range_to_invest,
            'max_close_rate': result['settlement_info']['max_close_rate']
        })

for stock in low_volatility_stocks:
    print(f'  {stock["code"]} - {stock["name"]} ({stock["status"]})')
    print(f'    价格比值: {stock["close_ratio"]:.4f}, 区间/投资价比: {stock["range_to_invest"]*100:.1f}%')
    print(f'    持有期间最高涨幅: {stock["max_close_rate"]*100:.1f}%')

# 分析止盈过大的股票
print('\n2. 止盈过大导致投资失败的股票:')
high_target_stocks = []
for stock in stock_data:
    stock_info = stock['stock_info']
    result = stock['results'][0]
    
    # 如果持有期间最高涨幅远小于止盈目标，说明止盈过大
    max_close_rate = result['settlement_info']['max_close_rate']
    target_win_rate = result['target']['stop_win_rate']
    
    if max_close_rate < target_win_rate * 0.7:  # 最高涨幅不到止盈目标的70%
        high_target_stocks.append({
            'code': stock_info['code'],
            'name': stock_info['name'],
            'status': result['status'],
            'target_win_rate': target_win_rate,
            'max_close_rate': max_close_rate,
            'close_ratio': result['freeze_data_stats']['close_ratio']
        })

for stock in high_target_stocks:
    print(f'  {stock["code"]} - {stock["name"]} ({stock["status"]})')
    print(f'    止盈目标: {stock["target_win_rate"]*100:.1f}%, 实际最高涨幅: {stock["max_close_rate"]*100:.1f}%')
    print(f'    Freeze期间价格比值: {stock["close_ratio"]:.4f}')
