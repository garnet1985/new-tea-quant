#!/usr/bin/env python3
"""
回调系统使用示例
"""
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import DatabaseManager
from app.data_source.providers.tushare.main import Tushare

def on_data_renew_complete():
    """数据更新完成后的回调函数"""
    logger.info("🎉 数据更新完成！开始执行后续任务...")
    
    # 这里可以添加你需要在数据更新完成后执行的函数
    # 例如：
    # - 运行策略分析
    # - 生成报告
    # - 发送通知
    # - 清理临时文件
    # - 等等...
    
    logger.info("✅ 后续任务执行完成")

def on_data_renew_complete_with_stats():
    """带统计信息的回调函数"""
    logger.info("📊 数据更新完成，开始生成统计报告...")
    
    # 获取数据库统计信息
    db = DatabaseManager()
    stats = db.get_stats()
    logger.info(f"数据库统计: {stats}")
    
    # 这里可以添加更多统计逻辑
    logger.info("📈 统计报告生成完成")

def example_usage():
    """使用示例"""
    logger.info("🚀 开始数据更新流程...")
    
    # 初始化数据库
    db = DatabaseManager()
    db.initialize()
    
    # 添加回调函数
    db.add_global_callback(on_data_renew_complete)
    db.add_global_callback(on_data_renew_complete_with_stats)
    
    # 创建Tushare实例并更新数据
    tushare = Tushare(db)
    tushare.renew_data()
    
    # 注意：不需要手动调用 wait_for_writes()，因为 renew_data() 内部已经调用了
    # 回调函数会在异步写入完成后自动执行
    
    logger.info("🏁 数据更新流程启动完成")

if __name__ == "__main__":
    example_usage() 