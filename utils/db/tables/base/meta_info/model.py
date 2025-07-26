from utils.db.db_model import BaseTableModel

class MetaInfoModel(BaseTableModel):
    def __init__(self, table_name: str, table_type: str, connected_db):
        super().__init__(table_name, table_type, connected_db)

    def get_meta_info(self, key: str):
        return self.find_one(f"key = %s", (key,)) 
    
    def set_meta_info(self, key: str, value: str):
        self.upsert_one({'key': key, 'value': value}, ['key'])