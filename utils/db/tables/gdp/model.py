from utils.db.db_model import BaseTableModel

class GDPModel(BaseTableModel):
    """GDP模型"""
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        self.is_base_table = True