from loguru import logger
from utils.db.db_manager import DatabaseManager
from app.data_source.providers.tushare.renewers.price_indexes.renewer import PriceIndexesRenewer
from app.data_source.providers.tushare.renewers.price_indexes.config import CONFIG
from app.data_source.providers.tushare.main import Tushare

# 临时修改为 overwrite 模式
CONFIG['renew_mode'] = 'overwrite'

db = DatabaseManager(is_verbose=False)
tu = Tushare(connected_db=db, is_verbose=False)

renewer = PriceIndexesRenewer(
    config=CONFIG,
    db=db,
    api=tu.api,
    storage=tu.storage,
    is_verbose=True
)

logger.info("测试更新 price_indexes (overwrite模式)...")
result = renewer.renew('20241031')

if result:
    logger.success("✅ 更新成功！")
    table = db.get_table_instance('price_indexes')
    records = table.load_many("1=1", order_by="date DESC", limit=5)
    logger.info(f"最新 5 条记录:")
    for r in records:
        logger.info(f"  {r['date']}: CPI={r.get('cpi')}, PPI={r.get('ppi')}, PMI={r.get('pmi')}")
else:
    logger.error("❌ 更新失败")
