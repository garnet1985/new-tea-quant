from utils.db import DatabaseManager
from datetime import datetime


class TushareStorage:
    def __init__(self, connected_db):
        self.db = connected_db

    def should_renew_stock_index(self):
        pass

    def save_stock_index(self, data):
        self.db.clear_table('stock_index')
        self.db.insert_data('stock_index', data)
        self.db.update_meta_info('stock_index_renew_date', datetime.now())