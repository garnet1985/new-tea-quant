"""
警告抑制工具
用于抑制第三方库的警告信息
"""

import warnings
import sys

def suppress_tushare_warnings():
    """抑制tushare库的FutureWarning"""
    warnings.filterwarnings('ignore', category=FutureWarning, module='tushare')
    warnings.filterwarnings('ignore', category=FutureWarning, message='.*fillna.*method.*')

def suppress_pandas_warnings():
    """抑制pandas相关的警告"""
    warnings.filterwarnings('ignore', category=FutureWarning, module='pandas')
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='pandas')

def suppress_all_third_party_warnings():
    """抑制所有第三方库的常见警告"""
    # tushare警告
    suppress_tushare_warnings()
    
    # pandas警告
    suppress_pandas_warnings()
    
    # 其他常见警告
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='numpy')

def setup_warning_suppression():
    """设置警告抑制（在程序启动时调用）"""
    suppress_all_third_party_warnings()
    
    # 如果是在开发环境，可以选择性地显示某些警告
    if '--show-warnings' in sys.argv:
        warnings.filterwarnings('default')  # 恢复默认警告行为 