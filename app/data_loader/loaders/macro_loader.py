"""
宏观经济数据加载器
"""
from typing import List, Dict, Any, Optional
from loguru import logger


class MacroEconomyLoader:
    """
    宏观经济数据加载器
    
    职责：
    - 宏观经济数据的读写操作
    - 宏观经济数据的查询
    """
    
    def __init__(self, db=None):
        """
        初始化宏观经济数据加载器
        
        Args:
            db: DatabaseManager实例，如果为None则自行创建
        """
        if db is not None:
            self.db = db
        else:
            from utils.db.db_manager import DatabaseManager
            self.db = DatabaseManager()
            self.db.initialize()
        
        self.gdp_model = self.db.get_table_instance('gdp')
        self.price_indexes_model = self.db.get_table_instance('price_indexes')
        self.lpr_model = self.db.get_table_instance('lpr')
        self.shibor_model = self.db.get_table_instance('shibor')
    
    def load_gdp(self, start_quarter: Optional[str] = None, end_quarter: Optional[str] = None) -> List[Dict]:
        """
        加载GDP数据
        
        Args:
            start_quarter: 开始季度（YYYYQ[1-4]格式，如2020Q1）
            end_quarter: 结束季度（YYYYQ[1-4]格式，如2024Q4）
            
        Returns:
            List[Dict]: GDP数据列表，包含gdp, gdp_yoy等字段
        """
        return self.gdp_model.load_GDP(start_quarter, end_quarter)
    
    def load_cpi(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        加载CPI数据
        
        Args:
            start_date: 开始月份（YYYYMM格式，如202001）
            end_date: 结束月份（YYYYMM格式，如202412）
            
        Returns:
            List[Dict]: CPI数据列表，包含cpi, cpi_yoy, cpi_mom等字段
        """
        return self.price_indexes_model.load_CPI(start_date, end_date)
    
    def load_ppi(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        加载PPI数据
        
        Args:
            start_date: 开始月份（YYYYMM格式，如202001）
            end_date: 结束月份（YYYYMM格式，如202412）
            
        Returns:
            List[Dict]: PPI数据列表，包含ppi, ppi_yoy, ppi_mom等字段
        """
        return self.price_indexes_model.load_PPI(start_date, end_date)
    
    def load_pmi(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        加载PMI数据
        
        Args:
            start_date: 开始月份（YYYYMM格式，如202001）
            end_date: 结束月份（YYYYMM格式，如202412）
            
        Returns:
            List[Dict]: PMI数据列表，包含pmi等字段
        """
        return self.price_indexes_model.load_PMI(start_date, end_date)
    
    def load_money_supply(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        加载货币供应量数据
        
        Args:
            start_date: 开始月份（YYYYMM格式，如202001）
            end_date: 结束月份（YYYYMM格式，如202412）
            
        Returns:
            List[Dict]: 货币供应量数据列表，包含m0, m1, m2及其同比环比数据
        """
        return self.price_indexes_model.load_money_supply(start_date, end_date)
    
    def load_price_indexes(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        加载完整的价格指数数据（包含CPI、PPI、PMI、货币供应量等所有字段）
        
        Args:
            start_date: 开始月份（YYYYMM格式，如202001）
            end_date: 结束月份（YYYYMM格式，如202412）
            
        Returns:
            List[Dict]: 价格指数数据列表，包含所有字段
        """
        return self.price_indexes_model.load_price_indexes(start_date, end_date)
    
    def load_lpr(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        加载LPR（贷款基础利率）数据
        
        Args:
            start_date: 开始日期（YYYYMMDD格式，如20200101）
            end_date: 结束日期（YYYYMMDD格式，如20241231）
            
        Returns:
            List[Dict]: LPR数据列表，包含lpr_1_y, lpr_5_y字段
        """
        return self.lpr_model.load_LPR(start_date, end_date)
    
    def load_shibor(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        加载Shibor（上海银行间同业拆放利率）数据
        
        Args:
            start_date: 开始日期（YYYYMMDD格式，如20200101）
            end_date: 结束日期（YYYYMMDD格式，如20241231）
            
        Returns:
            List[Dict]: Shibor数据列表，包含one_night, one_week, one_month等字段
        """
        return self.shibor_model.load_Shibor(start_date, end_date)
    
    def load(self, category: str, start_date: Optional[str] = None, 
            end_date: Optional[str] = None, start_quarter: Optional[str] = None, 
            end_quarter: Optional[str] = None) -> List[Dict]:
        """
        统一接口：根据类别加载宏观经济数据
        
        Args:
            category: 数据类别，支持：
                - 'gdp': GDP数据
                - 'cpi': CPI数据
                - 'ppi': PPI数据
                - 'pmi': PMI数据
                - 'money_supply': 货币供应量数据
                - 'price_indexes': 完整价格指数数据
                - 'lpr': LPR数据
                - 'shibor': Shibor数据
            start_date: 开始日期/月份（GDP使用start_quarter）
            end_date: 结束日期/月份（GDP使用end_quarter）
            start_quarter: GDP专用：开始季度（YYYYQ[1-4]格式）
            end_quarter: GDP专用：结束季度（YYYYQ[1-4]格式）
            
        Returns:
            List[Dict]: 宏观经济数据列表
            
        Raises:
            ValueError: 如果category不支持
        """
        category_map = {
            'gdp': self.load_gdp,
            'cpi': self.load_cpi,
            'ppi': self.load_ppi,
            'pmi': self.load_pmi,
            'money_supply': self.load_money_supply,
            'price_indexes': self.load_price_indexes,
            'lpr': self.load_lpr,
            'shibor': self.load_shibor,
        }
        
        if category not in category_map:
            raise ValueError(f"不支持的宏观经济数据类别: {category}. 支持的类别: {list(category_map.keys())}")
        
        if category == 'gdp':
            return category_map[category](start_quarter, end_quarter)
        else:
            return category_map[category](start_date, end_date)