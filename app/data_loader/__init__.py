"""
数据加载服务 - 全局数据服务工具

位置：app/data_loader/（应用层，与analyzer、data_source并列）

职责：
- 提供各种业务需求的数据服务
- 处理跨表操作和数据聚合
- 封装数据处理逻辑（复权、过滤、指标计算等）

使用方式：
    from app.data_loader import DataLoader
    
    # 方式1：传入db实例
    loader = DataLoader(db)
    df = loader.load_klines('000001.SZ', term='daily', adjust='qfq')
    
    # 方式2：自动创建db
    loader = DataLoader()
    klines_dict = loader.load_stock_klines_data('000001.SZ', settings)
    
    # 方式3：聚合所有数据
    all_data = loader.prepare_data(stock, settings)

架构说明：
- utils/db/ = 底层（连接、CRUD、单表操作）
- app/data_loader/ = 应用层（业务数据服务、跨表操作）
- app/analyzer/ = 应用层（策略分析）
- app/data_source/ = 应用层（数据源管理）
"""

from .data_loader import DataLoader

__all__ = ['DataLoader']

