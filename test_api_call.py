"""测试 Tushare API 调用"""
from loguru import logger
from app.data_source.providers.tushare.main import Tushare
from utils.db.db_manager import DatabaseManager

db = DatabaseManager(is_verbose=False)
tu = Tushare(connected_db=db, is_verbose=False)

# 测试不同的日期范围
test_cases = [
    ('202505', '202505', '单月范围'),
    ('202509', '202509', '最近月份'),
    ('202505', '202509', '多月范围'),
]

for start, end, desc in test_cases:
    print(f"\n{'='*80}")
    print(f"测试: {desc}")
    print(f"参数: start_m={start}, end_m={end}")
    print(f"{'='*80}")
    
    try:
        # CPI
        result_cpi = tu.api.cn_cpi(start_m=start, end_m=end)
        print(f"CPI: {len(result_cpi) if result_cpi is not None and not result_cpi.empty else 0} 条")
        if result_cpi is not None and not result_cpi.empty:
            print(f"  字段: {result_cpi.columns.tolist()}")
            print(f"  示例: {result_cpi.head(1).to_dict('records')}")
        
        # PPI
        result_ppi = tu.api.cn_ppi(start_m=start, end_m=end)
        print(f"PPI: {len(result_ppi) if result_ppi is not None and not result_ppi.empty else 0} 条")
        
        # PMI
        result_pmi = tu.api.cn_pmi(start_m=start, end_m=end)
        print(f"PMI: {len(result_pmi) if result_pmi is not None and not result_pmi.empty else 0} 条")
        
        # 货币供应
        result_m = tu.api.cn_m(start_m=start, end_m=end)
        print(f"货币供应: {len(result_m) if result_m is not None and not result_m.empty else 0} 条")
        
    except Exception as e:
        logger.error(f"❌ API调用失败: {e}")
