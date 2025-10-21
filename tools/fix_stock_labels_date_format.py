#!/usr/bin/env python3
"""
修复stock_labels表的日期格式，从YYYY-MM-DD改为YYYYMMDD
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.db.db_manager import DatabaseManager
from loguru import logger

def fix_stock_labels_date_format():
    """修复stock_labels表的日期格式"""
    
    db = DatabaseManager(use_connection_pool=True)
    
    try:
        logger.info("开始修复stock_labels表的日期格式...")
        
        # 1. 创建备份表
        logger.info("创建备份表...")
        db.execute_sync_query("""
            CREATE TABLE stock_labels_backup AS 
            SELECT * FROM stock_labels
        """)
        
        # 2. 修改原表结构 - 先改为更大的varchar
        logger.info("修改表结构...")
        db.execute_sync_query("""
            ALTER TABLE stock_labels 
            MODIFY COLUMN label_date VARCHAR(20) NOT NULL
        """)
        
        # 3. 转换日期格式
        logger.info("转换日期格式...")
        db.execute_sync_query("""
            UPDATE stock_labels 
            SET label_date = REPLACE(label_date, '-', '')
        """)
        
        # 4. 再次修改表结构 - 改为8位varchar
        logger.info("优化表结构...")
        db.execute_sync_query("""
            ALTER TABLE stock_labels 
            MODIFY COLUMN label_date VARCHAR(8) NOT NULL
        """)
        
        # 4. 验证结果
        logger.info("验证修复结果...")
        result = db.execute_sync_query("SELECT label_date FROM stock_labels LIMIT 5")
        logger.info("修复后的日期格式:")
        for record in result:
            logger.info(f"  日期: {record['label_date']} (类型: {type(record['label_date'])})")
        
        # 5. 检查数据完整性
        backup_count = db.execute_sync_query("SELECT COUNT(*) as count FROM stock_labels_backup")[0]['count']
        current_count = db.execute_sync_query("SELECT COUNT(*) as count FROM stock_labels")[0]['count']
        
        logger.info(f"备份表记录数: {backup_count}")
        logger.info(f"当前表记录数: {current_count}")
        
        if backup_count == current_count:
            logger.success("数据完整性验证通过！")
            logger.info("可以删除备份表: DROP TABLE stock_labels_backup")
        else:
            logger.error("数据完整性验证失败！请检查数据。")
            
        logger.success("stock_labels表日期格式修复完成！")
        
    except Exception as e:
        logger.error(f"修复失败: {e}")
        logger.info("如需恢复，请执行: DROP TABLE stock_labels; RENAME TABLE stock_labels_backup TO stock_labels;")
        raise

if __name__ == "__main__":
    fix_stock_labels_date_format()
