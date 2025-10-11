"""
GDP更新器

使用 Tushare 的 cn_gdp 接口获取GDP数据
"""

from ...base_renewer import BaseRenewer


class GDPRenewer(BaseRenewer):
    """
    GDP更新器
    
    特点：
    - 单API，直接使用基类默认行为
    - 不需要复写任何方法
    - 季度数据，有披露延迟
    """
    pass
