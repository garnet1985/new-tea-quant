"""
测试 LPR, GDP, Shibor 这3个宏观数据 renewer
"""
from loguru import logger
from utils.db.db_manager import DatabaseManager
from app.data_source.providers.tushare.main import Tushare

# 导入 renewers
from app.data_source.providers.tushare.renewers.lpr.renewer import LPRRenewer
from app.data_source.providers.tushare.renewers.lpr.config import CONFIG as LPR_CONFIG
from app.data_source.providers.tushare.renewers.gdp.renewer import GDPRenewer
from app.data_source.providers.tushare.renewers.gdp.config import CONFIG as GDP_CONFIG
from app.data_source.providers.tushare.renewers.shibor.renewer import ShiborRenewer
from app.data_source.providers.tushare.renewers.shibor.config import CONFIG as SHIBOR_CONFIG

def test_renewer(name, Renewer, config, latest_market_open_day):
    """测试单个 renewer"""
    print(f"\n{'='*80}")
    print(f"测试: {name}")
    print(f"{'='*80}")
    
    db = DatabaseManager(is_verbose=False)
    tu = Tushare(connected_db=db, is_verbose=False)
    
    # 临时改为 overwrite 模式以便测试
    config['renew_mode'] = 'overwrite'
    
    renewer = Renewer(
        config=config,
        db=db,
        api=tu.api,
        storage=tu.storage,
        is_verbose=True
    )
    
    try:
        result = renewer.renew(latest_market_open_day)
        
        if result:
            logger.success(f"✅ {name} 更新成功")
            
            # 查看数据
            table = db.get_table_instance(config['table_name'])
            count = table.count()
            logger.info(f"   表中记录数: {count}")
            
            if count > 0:
                latest_records = table.load_many("1=1", order_by=f"{config['date']['field']} DESC", limit=3)
                logger.info(f"   最新 3 条记录:")
                for i, r in enumerate(latest_records, 1):
                    date_field = config['date']['field']
                    logger.info(f"     {i}. {r[date_field]}: {r}")
        else:
            logger.error(f"❌ {name} 更新失败")
            
    except Exception as e:
        logger.error(f"❌ {name} 测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("="*80)
    print("🧪 测试 LPR, GDP, Shibor 宏观数据 renewers")
    print("="*80)
    
    latest_market_open_day = '20241031'  # 使用一个稳定的历史日期
    
    # 测试 LPR
    test_renewer('LPR', LPRRenewer, LPR_CONFIG, latest_market_open_day)
    
    # 测试 GDP
    test_renewer('GDP', GDPRenewer, GDP_CONFIG, latest_market_open_day)
    
    # 测试 Shibor
    test_renewer('Shibor', ShiborRenewer, SHIBOR_CONFIG, latest_market_open_day)
    
    print(f"\n{'='*80}")
    print("✅ 所有测试完成")
    print("="*80)

if __name__ == '__main__':
    main()

