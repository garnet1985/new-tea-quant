import os
import json

from loguru import logger
from utils.db.db_model import BaseTableModel

class HLMetaModel(BaseTableModel):
    """HistoricLow策略的元数据表模型"""
    
    def __init__(self, connected_db):
        # 设置表名和前缀
        table_name = "meta"
        table_prefix = "HL"
        self.table_full_name = f"{table_prefix}_{table_name}"

        # 调用父类构造函数
        super().__init__(table_name, connected_db)
        
        # 注册表到数据库管理器，使其在初始化时自动创建
        self.db.register_table(
            table_name=table_name,
            prefix=table_prefix,
            schema=self.schema,
            model_class=self.__class__
        )
        
    def load_schema(self) -> dict:
        """加载表结构定义"""
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(current_dir, 'schema.json')
        
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
                if self.db.is_verbose:
                    logger.info(f"Schema loaded for {self.table_name}: {schema_path}")
                return schema
        except Exception as e:
            logger.error(f"Failed to load schema from {schema_path}: {e}")
            return None
    
    def get_latest_meta(self):
        """获取最新的元数据"""
        return self.load_one(order_by="dateTime DESC")
    
    def update_meta(self, date: str, last_opportunity_update_time: str, last_suggested_stock_codes: list):
        """更新元数据"""
        data = {
            'date': date,
            'dateTime': 'NOW()',  # 使用数据库的当前时间
            'lastOpportunityUpdateTime': last_opportunity_update_time,
            'lastSuggestedStockCodes': json.dumps(last_suggested_stock_codes)
        }
        
        # 使用replace确保唯一性（基于date字段）
        return self.replace_one(data, unique_keys=['date'])