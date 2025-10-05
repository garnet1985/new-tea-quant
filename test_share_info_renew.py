#!/usr/bin/env python3
"""
测试股本信息更新功能
"""
import asyncio
from utils.db.db_manager import DatabaseManager
from app.data_source.data_source_manager import DataSourceManager


async def test_share_info_renew():
    """测试股本信息更新"""
    print("=== 测试股本信息更新功能 ===")
    
    # 连接数据库
    db = DatabaseManager()
    db.connect_sync()
    
    try:
        # 创建数据源管理器
        data_manager = DataSourceManager(db, is_verbose=True)
        
        # 只更新股本信息
        print("开始更新股本信息...")
        await data_manager.renew_data(['share_info'])
        
        print("✅ 股本信息更新测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.disconnect_sync()


if __name__ == "__main__":
    asyncio.run(test_share_info_renew())
