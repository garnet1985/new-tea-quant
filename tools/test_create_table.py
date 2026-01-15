#!/usr/bin/env python3
"""
测试表创建脚本 - 用于调试表创建问题
"""
import sys
import json
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.migrate_duckdb_to_postgresql import PostgreSQLSchemaAdapter, load_pg_config
import psycopg2

def test_create_tag_value_table():
    """测试创建 tag_value 表"""
    logger.info("测试创建 tag_value 表...")
    
    # 加载配置
    pg_config = load_pg_config()
    
    # 读取 schema
    schema_file = project_root / "app" / "core" / "modules" / "data_manager" / "base_tables" / "tag_value" / "schema.json"
    with schema_file.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    
    # 生成 SQL
    create_sql = PostgreSQLSchemaAdapter.generate_create_table_sql(schema)
    logger.info(f"\n生成的 SQL:\n{create_sql}\n")
    
    # 连接 PostgreSQL
    conn = psycopg2.connect(
        host=pg_config["host"],
        port=pg_config["port"],
        database=pg_config["database"],
        user=pg_config["user"],
        password=pg_config["password"]
    )
    
    try:
        with conn.cursor() as cursor:
            # 检查表是否存在
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s
            """, ("tag_value",))
            exists = cursor.fetchone()[0] > 0
            logger.info(f"表是否存在: {exists}")
            
            if exists:
                logger.info("表已存在，先删除...")
                cursor.execute("DROP TABLE IF EXISTS tag_value CASCADE;")
                conn.commit()
            
            # 创建表
            logger.info("执行 CREATE TABLE...")
            cursor.execute(create_sql)
            conn.commit()
            logger.info("✅ 表创建成功")
            
            # 验证表是否存在
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s
            """, ("tag_value",))
            exists_after = cursor.fetchone()[0] > 0
            logger.info(f"创建后表是否存在: {exists_after}")
            
            if exists_after:
                # 查看表结构
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'tag_value'
                    ORDER BY ordinal_position
                """)
                columns = cursor.fetchall()
                logger.info("\n表结构:")
                for col in columns:
                    logger.info(f"  {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
            else:
                logger.error("❌ 表创建后验证失败")
                
    except Exception as e:
        logger.error(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    test_create_tag_value_table()
