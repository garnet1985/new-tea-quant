from app.data_source.providers.tushare.main import Tushare
from app.data_source.providers.akshare.main import AKShare

class DataSourceManager:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.db = connected_db
        self.is_verbose = is_verbose

        self.sources = {
            'tushare': Tushare(connected_db, is_verbose),
            'akshare': AKShare(connected_db, is_verbose),
        }

        # global data memory cache
        self.latest_market_open_day = None
        self.latest_stock_index = None

    def get_source(self, source_name: str):
        return self.sources[source_name]()

    def renew_data(self):
        tu = self.sources['tushare']
        ak = self.sources['akshare']


        self.latest_stock_index = tu.renew_stock_index()
        self.latest_market_open_day = tu.get_latest_market_open_day()

        tu.renew_stock_K_lines(self.latest_market_open_day, self.latest_stock_index)
        ak.renew_stock_K_line_factors(self.latest_market_open_day, self.latest_stock_index)

        # below are not implemented yet
        tu.renew_global_economic_data()
        tu.renew_corporate_finance_data()

