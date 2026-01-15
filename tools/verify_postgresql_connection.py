#!/usr/bin/env python3
"""
PostgreSQL 连接验证脚本

验证 PostgreSQL 数据库连接是否正常，并检查基本功能。
"""
import sys
import json
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    logger.error("❌ 未安装 psycopg2，请运行: pip install psycopg2-binary")
    sys.exit(1)


def load_pg_config():
    """加载 PostgreSQL 配置"""
    config_path = project_root / "config" / "database" / "pg_config.json"
    
    if not config_path.exists():
        logger.error(f"❌ PostgreSQL 配置文件不存在: {config_path}")
        logger.info("请确保已创建 config/database/pg_config.json")
        sys.exit(1)
    
    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 优先使用 postgresql 配置，如果没有则使用 stocks_user
        pg_config = config.get("postgresql") or config.get("stocks_user")
        
        if not pg_config:
            logger.error("❌ 配置文件中未找到 postgresql 或 stocks_user 配置")
            sys.exit(1)
        
        return pg_config
    except Exception as e:
        logger.error(f"❌ 加载配置失败: {e}")
        sys.exit(1)


def test_connection(config):
    """测试数据库连接"""
    logger.info("🔌 正在测试 PostgreSQL 连接...")
    
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
        
        logger.info("✅ 连接成功！")
        
        # 测试查询
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            logger.info(f"📊 PostgreSQL 版本: {version['version']}")
            
            # 检查数据库编码
            cursor.execute("SHOW server_encoding;")
            encoding = cursor.fetchone()
            logger.info(f"📊 数据库编码: {encoding['server_encoding']}")
            
            # 列出所有表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            if tables:
                logger.info(f"📋 当前数据库中的表 ({len(tables)} 个):")
                for table in tables:
                    logger.info(f"   - {table['table_name']}")
            else:
                logger.info("📋 当前数据库中没有表（这是正常的，迁移后会创建表）")
        
        conn.close()
        logger.info("✅ 连接测试完成！")
        return True
        
    except psycopg2.OperationalError as e:
        logger.error(f"❌ 连接失败: {e}")
        logger.info("\n💡 请检查：")
        logger.info("   1. PostgreSQL 服务是否正在运行")
        logger.info("   2. 连接信息是否正确（host, port, database, user, password）")
        logger.info("   3. 用户是否有访问数据库的权限")
        return False
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


def test_basic_operations(config):
    """测试基本操作（创建测试表、插入、查询、删除）"""
    logger.info("\n🧪 正在测试基本操作...")
    
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 创建测试表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _migration_test (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✅ 创建测试表成功")
            
            # 插入数据
            cursor.execute("""
                INSERT INTO _migration_test (name) 
                VALUES (%s) 
                ON CONFLICT DO NOTHING;
            """, ("test_record",))
            logger.info("✅ 插入数据成功")
            
            # 查询数据
            cursor.execute("SELECT * FROM _migration_test WHERE name = %s;", ("test_record",))
            result = cursor.fetchone()
            if result:
                logger.info(f"✅ 查询数据成功: {result}")
            
            # 删除测试表
            cursor.execute("DROP TABLE IF EXISTS _migration_test;")
            logger.info("✅ 删除测试表成功")
        
        conn.commit()
        conn.close()
        logger.info("✅ 基本操作测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 基本操作测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("PostgreSQL 连接验证")
    logger.info("=" * 60)
    
    # 加载配置
    config = load_pg_config()
    logger.info(f"\n📝 配置信息:")
    logger.info(f"   主机: {config['host']}")
    logger.info(f"   端口: {config['port']}")
    logger.info(f"   数据库: {config['database']}")
    logger.info(f"   用户: {config['user']}")
    
    # 测试连接
    if not test_connection(config):
        sys.exit(1)
    
    # 测试基本操作
    if not test_basic_operations(config):
        sys.exit(1)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 所有测试通过！PostgreSQL 已准备就绪，可以开始迁移。")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
