"""
Shibor更新器

使用 Tushare 的 shibor 接口获取上海银行间同业拆放利率数据
"""

from ...base_renewer import BaseRenewer


class ShiborRenewer(BaseRenewer):
    """
    Shibor更新器
    
    特点：
    - 单API，直接使用基类默认行为
    - 不需要复写任何方法
    - 日度数据（每个工作日发布）
    """
    pass
