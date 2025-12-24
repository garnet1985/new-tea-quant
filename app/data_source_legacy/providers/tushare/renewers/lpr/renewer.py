"""
LPR利率更新器

使用 Tushare 的 shibor_lpr 接口获取贷款基准利率数据
"""

from ...base_renewer import BaseRenewer


class LPRRenewer(BaseRenewer):
    """
    LPR利率更新器
    
    特点：
    - 单API，直接使用基类默认行为
    - 不需要复写任何方法
    - 日度数据（但不是每天都有发布）
    """
    pass
