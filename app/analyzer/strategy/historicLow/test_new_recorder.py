#!/usr/bin/env python3
"""
测试新的investment_recorder功能
"""
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

from decimal import Decimal
from investment_recorder import InvestmentRecorder

def test_new_recorder():
    """测试新的recorder功能"""
    print("🧪 测试新的investment_recorder功能...")
    
    # 创建投资记录器
    recorder = InvestmentRecorder(tmp_dir="tmp_test_new")
    
    # 模拟投资数据
    mock_investment = {
        'invest_start_date': '20230711',
        'goal': {
            'purchase': Decimal('13.19'),
            'win': Decimal('19.78'),
            'loss': Decimal('10.55')
        },
        'historic_low_ref': {
            'record': {
                'date': '20221031',
                'lowest': Decimal('12.57')
            },
            'term': 60
        }
    }
    
    mock_stock = {
        'id': '000002.SZ',
        'name': '万科A',
        'market': '主板'
    }
    
    # 模拟K线数据
    mock_kline_data = {
        'daily': [
            {'date': '20221031', 'open': 12.80, 'close': 12.90, 'highest': 13.00, 'lowest': 12.57},
            {'date': '20230711', 'open': 13.10, 'close': 13.19, 'highest': 13.25, 'lowest': 13.00}
        ],
        'monthly': []
    }
    
    # 测试记录成功的投资
    print("📈 测试记录成功的投资...")
    recorder.record_investment_settlement(mock_stock, mock_investment, 'win', 15.50, '20230801', mock_kline_data)
    
    # 测试记录失败的投资
    print("📉 测试记录失败的投资...")
    recorder.record_investment_settlement(mock_stock, mock_investment, 'loss', 9.00, '20240115', mock_kline_data)
    
    # 测试记录open状态的投资
    print("⏳ 测试记录open状态的投资...")
    recorder.record_investment_settlement(mock_stock, mock_investment, 'open', 13.19, '20241231', mock_kline_data)
    
    # 获取摘要
    summary = recorder.get_summary()
    print(f"📊 投资记录摘要: {summary}")
    
    # 检查meta.json
    meta_file = os.path.join("tmp_test_new", "meta.json")
    if os.path.exists(meta_file):
        print(f"📋 meta.json已创建: {meta_file}")
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta_content = f.read()
            print(f"📄 meta.json内容:\n{meta_content}")
    
    print("✅ 新recorder功能测试完成！")
    print("🔍 请检查tmp_test_new目录下的文件结构")

if __name__ == "__main__":
    test_new_recorder()
