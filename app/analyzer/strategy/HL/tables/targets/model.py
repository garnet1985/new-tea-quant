import os
import json
from loguru import logger
from utils.db.db_model import BaseTableModel

class HLOpportunityHistoryModel(BaseTableModel):
    """HistoricLow策略的机会历史表模型"""
    
    def __init__(self, connected_db):
        # 设置表名和前缀
        table_name = "opportunity_history"
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

    def toDict(self, info):
        # info is a string like "key1=value1|key2=value2|key3=value3"
        # return a dict like {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        Dict = {}
        items = info.split('|')
        for item in items:
            key, value = item.split('=')
            Dict[key] = value
        return Dict

    def toStr(self, info, key, value):
        if info is None:
            return f"{key}={value}"
        # info is a string like "key1=value1|key2=value2|key3=value3"
        # return a string like "key1=value1|key2=value2|key3=value3|newkey=newvalue"
        info_dict = self.toDict(info)
        info_dict[key] = value
        return '|'.join([f"{k}={v}" for k, v in info_dict.items()])

    def get_meta_info(self, key: str):
        info = self.load_one()
        if info is None:
            return None
        else:
            info_dict = self.toDict(info['info'])
            return info_dict.get(key)

    def set_meta_info(self, key: str, value: str):
        # 获取第一条记录（如果存在）
        info = self.load_one()
        if info is None:
            # 如果记录不存在，创建新记录
            txt = f"{key}={value}"
            self.insert_one({'info': txt})
        else:
            # 如果记录存在，更新第一条记录
            txt = self.toStr(info['info'], key, value)
            # 使用基类的 update 方法
            self.update(
                {'info': txt},
                'id = %s',
                (info['id'],)
            ) 