"""
宏观经济服务（MacroService）

职责：
- 封装宏观经济相关的跨表查询和数据组装
- 提供领域级的业务方法

涉及的表：
- gdp: GDP数据（季度）
- price_indexes: 价格指数（CPI、PPI、PMI、货币供应量，月度）
- shibor: Shibor利率（日度）
- lpr: LPR利率（日度）
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from .. import BaseDataService


class MacroService(BaseDataService):
    """宏观经济数据服务"""
    
    # 指标分类映射
    INDICATOR_CATEGORIES = {
        'price_indexes': {  # 价格指数（月度）
            'cpi': ['cpi', 'cpi_yoy', 'cpi_mom'],  # 消费者价格指数
            'ppi': ['ppi', 'ppi_yoy', 'ppi_mom'],  # 生产者价格指数
            'pmi': ['pmi', 'pmi_l_scale', 'pmi_m_scale', 'pmi_s_scale'],  # 采购经理人指数
            'money_supply': ['m0', 'm0_yoy', 'm0_mom', 'm1', 'm1_yoy', 'm1_mom', 'm2', 'm2_yoy', 'm2_mom']  # 货币供应量
        },
        'gdp': [  # GDP数据（季度）
            'gdp', 'gdp_yoy', 
            'primary_industry', 'primary_industry_yoy',  # 第一产业
            'secondary_industry', 'secondary_industry_yoy',  # 第二产业
            'tertiary_industry', 'tertiary_industry_yoy'  # 第三产业
        ],
        'interest_rates': {  # 利率数据（日度）
            'shibor': ['one_night', 'one_week', 'one_month', 'three_month', 'one_year'],  # Shibor利率
            'lpr': ['lpr_1_y', 'lpr_5_y']  # LPR利率
        }
    }
    
    def __init__(self, data_manager: Any):
        """
        初始化宏观经济数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 获取相关 Model（通过 DataManager，自动绑定默认 db）- 私有属性，不对外暴露
        self._gdp = data_manager.get_table('gdp')
        self._price_indexes = data_manager.get_table('price_indexes')
        self._shibor = data_manager.get_table('shibor')
        self._lpr = data_manager.get_table('lpr')
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default(auto_init=True)
    
    # ==================== GDP 数据 ====================
    
    def load_gdp(
        self, 
        start_quarter: Optional[str] = None, 
        end_quarter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载GDP数据
        
        Args:
            start_quarter: 开始季度（YYYYQ[1-4]格式，如2020Q1）
            end_quarter: 结束季度（YYYYQ[1-4]格式，如2024Q4）
            
        Returns:
            GDP数据列表
        """
        if start_quarter and end_quarter:
            return self._gdp.load_by_date_range(start_quarter, end_quarter)
        elif start_quarter:
            return self._gdp.load(
                "quarter >= %s",
                (start_quarter,),
                order_by="quarter ASC"
            )
        elif end_quarter:
            return self._gdp.load(
                "quarter <= %s",
                (end_quarter,),
                order_by="quarter ASC"
            )
        else:
            return self._gdp.load(order_by="quarter ASC")
    
    def load_latest_gdp(self) -> Optional[Dict[str, Any]]:
        """
        加载最新GDP数据
        
        Returns:
            最新GDP数据，如果不存在返回 None
        """
        return self._gdp.load_latest()
    
    def load_gdp_by_quarter(self, quarter: str) -> Optional[Dict[str, Any]]:
        """
        加载指定季度的GDP数据
        
        Args:
            quarter: 季度（YYYYQ[1-4]格式，如2020Q1）
            
        Returns:
            GDP数据，如果不存在返回 None
        """
        return self._gdp.load_by_quarter(quarter)
    
    # ==================== 价格指数（CPI、PPI、PMI、货币供应量）====================
    
    def _load_price_indexes(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        加载价格指数数据（通用方法）
        
        Args:
            start_date: 开始月份（YYYYMM格式，如202001）
            end_date: 结束月份（YYYYMM格式，如202412）
            fields: 需要返回的字段列表（如果为None，返回所有字段）
            
        Returns:
            价格指数数据列表（只包含指定的字段，如果fields为None则包含所有字段）
        """
        condition = "1=1"
        params = []
        
        if start_date:
            condition += " AND date >= %s"
            params.append(start_date)
        if end_date:
            condition += " AND date <= %s"
            params.append(end_date)
        
        # 加载数据
        data = self._price_indexes.load(
            condition,
            tuple(params) if params else (),
            order_by="date ASC"
        )
        
        # 如果指定了字段，只返回这些字段（始终包含date字段）
        if fields:
            result_fields = ['date'] + fields
            return [
                {k: v for k, v in item.items() if k in result_fields}
                for item in data
            ]
        
        return data
    
    def load_cpi(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载CPI数据
        
        Args:
            start_date: 开始月份（YYYYMM格式，如202001）
            end_date: 结束月份（YYYYMM格式，如202412）
            
        Returns:
            CPI数据列表（只包含 date, cpi, cpi_yoy, cpi_mom 字段）
        """
        fields = self.INDICATOR_CATEGORIES['price_indexes']['cpi']
        return self._load_price_indexes(start_date, end_date, fields=fields)
    
    def load_ppi(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载PPI数据
        
        Args:
            start_date: 开始月份（YYYYMM格式，如202001）
            end_date: 结束月份（YYYYMM格式，如202412）
            
        Returns:
            PPI数据列表（只包含 date, ppi, ppi_yoy, ppi_mom 字段）
        """
        fields = self.INDICATOR_CATEGORIES['price_indexes']['ppi']
        return self._load_price_indexes(start_date, end_date, fields=fields)
    
    def load_pmi(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载PMI数据
        
        Args:
            start_date: 开始月份（YYYYMM格式，如202001）
            end_date: 结束月份（YYYYMM格式，如202412）
            
        Returns:
            PMI数据列表（只包含 date, pmi, pmi_l_scale, pmi_m_scale, pmi_s_scale 字段）
        """
        fields = self.INDICATOR_CATEGORIES['price_indexes']['pmi']
        return self._load_price_indexes(start_date, end_date, fields=fields)
    
    def load_money_supply(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载货币供应量数据
        
        Args:
            start_date: 开始月份（YYYYMM格式，如202001）
            end_date: 结束月份（YYYYMM格式，如202412）
            
        Returns:
            货币供应量数据列表（只包含 date, m0, m0_yoy, m0_mom, m1, m1_yoy, m1_mom, m2, m2_yoy, m2_mom 字段）
        """
        fields = self.INDICATOR_CATEGORIES['price_indexes']['money_supply']
        return self._load_price_indexes(start_date, end_date, fields=fields)
    
    # ==================== 利率数据（Shibor、LPR）====================
    
    def _load_rate_data(
        self,
        model,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载利率数据（通用方法，用于Shibor和LPR）
        
        Args:
            model: 利率数据Model（_shibor 或 _lpr）
            start_date: 开始日期（YYYYMMDD格式，如20200101）
            end_date: 结束日期（YYYYMMDD格式，如20241231）
            
        Returns:
            利率数据列表
        """
        if start_date and end_date:
            return model.load_by_date_range(start_date, end_date)
        elif start_date:
            return model.load(
                "date >= %s",
                (start_date,),
                order_by="date ASC"
            )
        elif end_date:
            return model.load(
                "date <= %s",
                (end_date,),
                order_by="date ASC"
            )
        else:
            return model.load(order_by="date ASC")
    
    def _load_rate_by_date(
        self,
        model,
        date: str,
        fallback: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        加载指定日期的利率数据（通用方法，支持回退）
        
        Args:
            model: 利率数据Model（_shibor 或 _lpr）
            date: 日期（YYYYMMDD格式）
            fallback: 如果指定日期没有数据，是否回退到最近的数据
            
        Returns:
            利率数据，如果不存在返回 None
        """
        if fallback:
            return model.load_by_date(date)  # Model 已实现回退逻辑
        else:
            return model.load_one("date = %s", (date,))
    
    def load_shibor(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载Shibor利率数据
        
        Args:
            start_date: 开始日期（YYYYMMDD格式，如20200101）
            end_date: 结束日期（YYYYMMDD格式，如20241231）
            
        Returns:
            Shibor利率数据列表
        """
        return self._load_rate_data(self._shibor, start_date, end_date)
    
    def load_shibor_by_date(self, date: str, fallback: bool = True) -> Optional[Dict[str, Any]]:
        """
        加载指定日期的Shibor利率（支持回退）
        
        Args:
            date: 日期（YYYYMMDD格式）
            fallback: 如果指定日期没有数据，是否回退到最近的数据
            
        Returns:
            Shibor利率数据，如果不存在返回 None
        """
        return self._load_rate_by_date(self._shibor, date, fallback)
    
    def load_latest_shibor(self) -> Optional[Dict[str, Any]]:
        """
        加载最新Shibor利率
        
        Returns:
            最新Shibor利率数据，如果不存在返回 None
        """
        return self._shibor.load_latest()
    
    def load_lpr(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载LPR利率数据
        
        Args:
            start_date: 开始日期（YYYYMMDD格式，如20200101）
            end_date: 结束日期（YYYYMMDD格式，如20241231）
            
        Returns:
            LPR利率数据列表
        """
        return self._load_rate_data(self._lpr, start_date, end_date)
    
    def load_lpr_by_date(self, date: str, fallback: bool = True) -> Optional[Dict[str, Any]]:
        """
        加载指定日期的LPR利率（支持回退）
        
        Args:
            date: 日期（YYYYMMDD格式）
            fallback: 如果指定日期没有数据，是否回退到最近的数据
            
        Returns:
            LPR利率数据，如果不存在返回 None
        """
        return self._load_rate_by_date(self._lpr, date, fallback)
    
    def load_latest_lpr(self) -> Optional[Dict[str, Any]]:
        """
        加载最新LPR利率
        
        Returns:
            最新LPR利率数据，如果不存在返回 None
        """
        return self._lpr.load_latest()
    
    # ==================== 跨表查询（SQL JOIN）====================
    
    def load_risk_free_rate(
        self, 
        date: str, 
        prefer_shibor: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        加载无风险利率（优先使用 Shibor，如果没有则使用 LPR）
        
        Args:
            date: 日期（YYYYMMDD格式）
            prefer_shibor: 是否优先使用 Shibor（默认 True）
            
        Returns:
            利率数据字典，包含 source 字段标识数据来源
        """
        # 定义优先级顺序
        if prefer_shibor:
            sources = [
                (self.load_shibor_by_date, 'shibor'),
                (self.load_lpr_by_date, 'lpr')
            ]
        else:
            sources = [
                (self.load_lpr_by_date, 'lpr'),
                (self.load_shibor_by_date, 'shibor')
            ]
        
        # 按优先级尝试获取数据
        for load_func, source_name in sources:
            data = load_func(date, fallback=True)
            if data:
                data['source'] = source_name
                return data
        
        return None
    
    def load_macro_snapshot(self, date: str) -> Dict[str, Any]:
        """
        加载指定日期的宏观经济快照（所有指标）
        
        Args:
            date: 日期（YYYYMMDD格式）
            
        Returns:
            宏观经济快照字典，包含：
            - gdp: 最新GDP数据
            - cpi: 该月CPI数据
            - ppi: 该月PPI数据
            - pmi: 该月PMI数据
            - money_supply: 该月货币供应量数据
            - shibor: 该日Shibor利率
            - lpr: 该日LPR利率
            - risk_free_rate: 无风险利率（优先Shibor）
        """
        # 获取月份（用于月度指标）
        month = date[:6]  # YYYYMM
        
        # 获取季度（用于GDP）
        year = int(date[:4])
        month_num = int(date[4:6])
        quarter = f"{year}Q{(month_num - 1) // 3 + 1}"
        
        # 加载价格指数数据（一次性加载，包含所有指标）
        price_indexes_data = self._price_indexes.load_one("date = %s", (month,))
        
        snapshot = {
            'date': date,
            'gdp': self.load_gdp_by_quarter(quarter),
            'price_indexes': price_indexes_data,  # 包含 cpi, ppi, pmi, m0, m1, m2 等所有字段
            'shibor': self.load_shibor_by_date(date, fallback=True),
            'lpr': self.load_lpr_by_date(date, fallback=True),
            'risk_free_rate': self.load_risk_free_rate(date, prefer_shibor=True),
        }
        
        return snapshot
    
    # ==================== 批量操作 ====================
    
    def save_gdp_data(self, gdp_data: List[Dict[str, Any]]) -> int:
        """
        批量保存GDP数据（自动去重）
        
        Args:
            gdp_data: GDP数据列表
            
        Returns:
            影响的行数
        """
        return self._gdp.save_gdp_data(gdp_data)
    
    def save_shibor_data(self, shibor_data: List[Dict[str, Any]]) -> int:
        """
        批量保存Shibor数据（自动去重）
        
        Args:
            shibor_data: Shibor数据列表
            
        Returns:
            影响的行数
        """
        return self._shibor.save_shibor_data(shibor_data)
    
    def save_lpr_data(self, lpr_data: List[Dict[str, Any]]) -> int:
        """
        批量保存LPR数据（自动去重）
        
        Args:
            lpr_data: LPR数据列表
            
        Returns:
            影响的行数
        """
        return self._lpr.save_lpr_data(lpr_data) if hasattr(self._lpr, 'save_lpr_data') else self._lpr.replace(lpr_data, unique_keys=['date'])
    
    def save_price_indexes_data(self, price_indexes_data: List[Dict[str, Any]]) -> int:
        """
        批量保存价格指数数据（自动去重）
        
        Args:
            price_indexes_data: 价格指数数据列表
            
        Returns:
            影响的行数
        """
        return self._price_indexes.save_price_indexes(price_indexes_data)

