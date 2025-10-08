"""
Share Info Model - 股本信息模型
"""
from utils.db.db_model import BaseTableModel


class ShareInfoModel(BaseTableModel):
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        self.is_base_table = True


