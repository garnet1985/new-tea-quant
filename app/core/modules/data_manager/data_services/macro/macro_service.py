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
    
    def __init__(self, data_manager: Any):
        """
        初始化宏观经济数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 获取相关 Model（通过 DataManager，自动绑定默认 db）- 私有属性，不对外暴露
        self._gdp = data_manager.get_model('gdp')
        self._price_indexes = data_manager.get_model('price_indexes')
        self._shibor = data_manager.get_model('shibor')
        self._lpr = data_manager.get_model('lpr')
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from app.core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default()
    
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
            CPI数据列表（包含 cpi, cpi_yoy, cpi_mom 字段）
        """
        condition = "1=1"
        params = []
        
        if start_date:
            condition += " AND date >= %s"
            params.append(start_date)
        if end_date:
            condition += " AND date <= %s"
            params.append(end_date)
        
        # price_indexes 表是扁平结构，所有指标在同一行
        # 返回所有字段，调用方可以只取 cpi 相关字段
        return self._price_indexes.load(
            condition,
            tuple(params) if params else (),
            order_by="date ASC"
        )
    
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
            PPI数据列表（包含 ppi, ppi_yoy, ppi_mom 字段）
        """
        condition = "1=1"
        params = []
        
        if start_date:
            condition += " AND date >= %s"
            params.append(start_date)
        if end_date:
            condition += " AND date <= %s"
            params.append(end_date)
        
        # price_indexes 表是扁平结构，所有指标在同一行
        return self._price_indexes.load(
            condition,
            tuple(params) if params else (),
            order_by="date ASC"
        )
    
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
            PMI数据列表（包含 pmi, pmi_l_scale, pmi_m_scale, pmi_s_scale 字段）
        """
        condition = "1=1"
        params = []
        
        if start_date:
            condition += " AND date >= %s"
            params.append(start_date)
        if end_date:
            condition += " AND date <= %s"
            params.append(end_date)
        
        # price_indexes 表是扁平结构，所有指标在同一行
        return self._price_indexes.load(
            condition,
            tuple(params) if params else (),
            order_by="date ASC"
        )
    
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
            货币供应量数据列表（包含 m0, m0_yoy, m0_mom, m1, m1_yoy, m1_mom, m2, m2_yoy, m2_mom 字段）
        """
        condition = "1=1"
        params = []
        
        if start_date:
            condition += " AND date >= %s"
            params.append(start_date)
        if end_date:
            condition += " AND date <= %s"
            params.append(end_date)
        
        # price_indexes 表是扁平结构，所有指标在同一行
        return self._price_indexes.load(
            condition,
            tuple(params) if params else (),
            order_by="date ASC"
        )
    
    # ==================== 利率数据（Shibor、LPR）====================
    
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
        if start_date and end_date:
            return self._shibor.load_by_date_range(start_date, end_date)
        elif start_date:
            return self._shibor.load(
                "date >= %s",
                (start_date,),
                order_by="date ASC"
            )
        elif end_date:
            return self._shibor.load(
                "date <= %s",
                (end_date,),
                order_by="date ASC"
            )
        else:
            return self._shibor.load(order_by="date ASC")
    
    def load_shibor_by_date(self, date: str, fallback: bool = True) -> Optional[Dict[str, Any]]:
        """
        加载指定日期的Shibor利率（支持回退）
        
        Args:
            date: 日期（YYYYMMDD格式）
            fallback: 如果指定日期没有数据，是否回退到最近的数据
            
        Returns:
            Shibor利率数据，如果不存在返回 None
        """
        if fallback:
            return self._shibor.load_by_date(date)  # Model 已实现回退逻辑
        else:
            return self._shibor.load_one("date = %s", (date,))
    
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
        if start_date and end_date:
            return self._lpr.load_by_date_range(start_date, end_date)
        elif start_date:
            return self._lpr.load(
                "date >= %s",
                (start_date,),
                order_by="date ASC"
            )
        elif end_date:
            return self._lpr.load(
                "date <= %s",
                (end_date,),
                order_by="date ASC"
            )
        else:
            return self._lpr.load(order_by="date ASC")
    
    def load_lpr_by_date(self, date: str, fallback: bool = True) -> Optional[Dict[str, Any]]:
        """
        加载指定日期的LPR利率（支持回退）
        
        Args:
            date: 日期（YYYYMMDD格式）
            fallback: 如果指定日期没有数据，是否回退到最近的数据
            
        Returns:
            LPR利率数据，如果不存在返回 None
        """
        if fallback:
            return self._lpr.load_by_date(date)  # Model 已实现回退逻辑
        else:
            return self._lpr.load_one("date = %s", (date,))
    
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
        if prefer_shibor:
            shibor = self.load_shibor_by_date(date, fallback=True)
            if shibor:
                shibor['source'] = 'shibor'
                return shibor
            
            lpr = self.load_lpr_by_date(date, fallback=True)
            if lpr:
                lpr['source'] = 'lpr'
                return lpr
        else:
            lpr = self.load_lpr_by_date(date, fallback=True)
            if lpr:
                lpr['source'] = 'lpr'
                return lpr
            
            shibor = self.load_shibor_by_date(date, fallback=True)
            if shibor:
                shibor['source'] = 'shibor'
                return shibor
        
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

