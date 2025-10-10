"""
企业财务指标更新器

使用Tushare的fina_indicator接口获取企业财务指标数据

设计：
- config使用lambda表达式做值转换（end_date → quarter）
- 只复写get_job_primary_keys（处理主键生成）
- 其他逻辑完全使用基类默认行为
"""

from typing import Dict, List, Optional
from ...base_renewer import BaseRenewer


class CorporateFinanceRenewer(BaseRenewer):
    """
    企业财务指标更新器
    
    极简设计：
    - ✅ config的lambda表达式处理值转换（end_date → quarter）
    - ✅ 只复写get_job_primary_keys（返回{'id': ...}）
    - ✅ 其他逻辑使用基类默认行为
    """
    
    def get_job_primary_keys(self, stock: Dict, db_record: Optional[Dict],
                             primary_keys: List[str]) -> Dict:
        """
        生成job的主键
        
        为什么复写？
        - 主键是['id', 'quarter']
        - stock_list只有id，没有quarter
        - quarter由API返回数据提供（每行记录可能是不同季度）
        
        Returns:
            Dict: 只返回{'id': ...}，不包含quarter
        """
        return {'id': stock['id']}
