"""
企业财务指标更新器

极简设计（仅40行）：
- Lambda表达式处理值转换（end_date → quarter）
- Hook函数处理主键生成（只返回id）
- 其他逻辑完全使用基类默认行为

设计思想：
- 内部统一YYYYMMDD格式
- 边界查询config转换格式
- storage_format: quarter → YYYYMMDD（读取时）
- api_format: YYYYMMDD → date（API请求时）
- mapping: date → quarter（保存时）
"""

from typing import Dict, List, Optional
from ...base_renewer import BaseRenewer


class CorporateFinanceRenewer(BaseRenewer):
    """
    企业财务指标更新器（极简版）
    
    只需复写1个方法：
    - get_job_primary_keys: 返回{'id': ...}（quarter由API数据提供）
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
