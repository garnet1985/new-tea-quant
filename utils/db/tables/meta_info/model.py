from utils.db.db_model import BaseTableModel

class MetaInfoModel(BaseTableModel):
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)

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
            # 使用UPDATE语句更新第一条记录，而不是replace_one
            update_sql = "UPDATE meta_info SET info = %s WHERE id = %s"
            self.db.execute_sync_update(update_sql, (txt, info['id']))

