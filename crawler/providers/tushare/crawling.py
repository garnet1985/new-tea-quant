class TushareCrawling:
    def __init__(self):
        self.token = self.get_token()

    def get_token(self):
        with open('crawler/providers/tushare/auth/token.txt', 'r') as f:
            return f.read()


    # Stock APIs

    def get_data(self, code, start_date, end_date):
        pass

    def request_stock_index(self):
        pass

    def request_stock(self):
        pass

    def request_stock_daily(self):
        pass

    def request_stock_weekly(self):
        pass

    def request_stock_monthly(self):
        pass

    def request_stocks(self):
        pass

    def request_stocks_daily(self):
        pass

    def request_stocks_weekly(self):
        pass

    def request_stocks_monthly(self):
        pass

    # Financial APIs