"""
测试 price_indexes renewer
"""
from loguru import logger
from utils.db.db_manager import DatabaseManager
from app.data_source.providers.tushare.renewers.price_indexes.renewer import PriceIndexesRenewer
from app.data_source.providers.tushare.renewers.price_indexes.config import CONFIG
from app.data_source.providers.tushare.main import Tushare

def test_price_indexes():
    print("="*80)
    print("🧪 测试 price_indexes renewer")
    print("="*80)
    print()
    
    # 初始化
    db = DatabaseManager(is_verbose=False)
    
    # 创建 Tushare API
    tu = Tushare(connected_db=db, is_verbose=True)
    
    # 创建 renewer
    renewer = PriceIndexesRenewer(
        config=CONFIG,
        db=db,
        api=tu.api,
        storage=tu.storage,
        is_verbose=True
    )
    
    # 测试更新
    logger.info("开始测试更新...")
    
    # 使用一个近期的日期测试
    latest_market_open_day = '20241031'  # 2024年10月31日
    
    try:
        result = renewer.renew(latest_market_open_day)
        
        if result:
            logger.success("✅ 更新成功！")
            
            # 验证数据
            table = db.get_table_instance('price_indexes')
            latest_records = table.load_many(
                condition="1=1",
                order_by="date DESC",
                limit=5
            )
            
            if latest_records:
                logger.info(f"\n最新 5 条记录:")
                for i, record in enumerate(latest_records, 1):
                    logger.info(f"  {i}. {record['date']}: CPI={record.get('cpi')}, PPI={record.get('ppi')}, PMI={record.get('pmi')}")
            
        else:
            logger.error("❌ 更新失败")
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_price_indexes()

