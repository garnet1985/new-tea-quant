"""重建 industry_capital_flow 表"""
from utils.db.db_manager import DatabaseManager

db = DatabaseManager(is_verbose=False)

print("重建 industry_capital_flow 表...")

# 删除旧表
db.execute_sync_query("DROP TABLE IF EXISTS industry_capital_flow")
print("✅ 旧表已删除")

# 重新创建表（使用新的 schema）
table = db.get_table_instance('industry_capital_flow')
print("✅ 新表已创建")

# 检查新表结构
result = db.execute_sync_query("SHOW CREATE TABLE industry_capital_flow")
print("\n新表结构:")
print(result[0]['Create Table'])
