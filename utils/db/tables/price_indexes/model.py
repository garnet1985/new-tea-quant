from utils.db.db_model import BaseTableModel



class PriceIndexesModel(BaseTableModel):
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True

    def renew_price_indexes(self, latest_market_open_day: str = None):
        pass
    
    def request_price_indexes(self):
        pass