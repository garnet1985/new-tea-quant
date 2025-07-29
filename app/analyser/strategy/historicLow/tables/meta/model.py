import os
import json

from loguru import logger
from utils.db.db_model import BaseTableModel

class HLMetaModel(BaseTableModel):
    def __init__(self, connected_db):
        self.table_name = "meta"
        self.table_prefix = "HL"
        super().register_table(self.table_name, self.table_prefix, super().load_schema())


    
    
    
