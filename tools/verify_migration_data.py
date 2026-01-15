#!/usr/bin/env python3
"""
验证迁移数据完整性脚本

对比 DuckDB 和 PostgreSQL 中每个表的数据数量，确保迁移成功。
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
from loguru import logger
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import duckdb
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError as e:
    logger.error(f"❌ 缺少依赖: {e}")
    logger.info("请运行: pip install psycopg2-binary duckdb")
    sys.exit(1)

from core.config.loaders.db_conf import load_duckdb_conf
from core.infra.db.db_schema_manager import DbSchemaManager


def load_pg_config(config_path: Path = None) -> Dict:
    """加载 PostgreSQL 配置"""
    if config_path:
        config_file = config_path
    else:
        config_file = project_root / "config" / "database" / "pg_config.json"
    
    if not config_file.exists():
        raise FileNotFoundError(f"PostgreSQL 配置文件不存在: {config_file}")
    
    with config_file.open("r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 优先使用 postgresql 配置
    pg_config = config.get("postgresql") or config.get("stocks_user")
    
    if not pg_config:
        raise ValueError("配置文件中未找到 postgresql 或 stocks_user 配置")
    
    return pg_config


def get_duckdb_tables(duckdb_conn) -> List[str]:
    """获取 DuckDB 中的所有表"""
    cursor = duckdb_conn.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'main'
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    return tables


def get_postgresql_tables(pg_conn) -> List[str]:
    """获取 PostgreSQL 中的所有表"""
    with pg_conn.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
    return tables


def get_table_count(conn, table_name: str, db_type: str) -> int:
    """获取表的记录数"""
    try:
        if db_type == "duckdb":
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            result = cursor.fetchone()
            return result[0] if result else 0
        else:  # postgresql
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                result = cursor.fetchone()
                return result[0] if result else 0
    except Exception as e:
        logger.warning(f"   ⚠️  获取表 {table_name} 记录数失败 ({db_type}): {e}")
        return -1  # 使用 -1 表示错误


def verify_tables(
    duckdb_conn,
    pg_conn,
    schema_manager: DbSchemaManager
) -> Dict[str, Dict]:
    """验证所有表的数据数量"""
    logger.info("=" * 60)
    logger.info("开始验证数据完整性")
    logger.info("=" * 60)
    
    # 获取表列表
    duckdb_tables = get_duckdb_tables(duckdb_conn)
    pg_tables = get_postgresql_tables(pg_conn)
    
    # 加载所有 schema，只验证有 schema 定义的表
    all_schemas = schema_manager.load_all_schemas()
    tables_to_verify = [t for t in duckdb_tables if t in all_schemas]
    
    logger.info(f"\n📋 待验证表 ({len(tables_to_verify)} 个):")
    for table in tables_to_verify:
        logger.info(f"   - {table}")
    
    results = {}
    all_match = True
    missing_in_pg = []
    missing_in_duckdb = []
    
    logger.info("\n" + "=" * 60)
    logger.info("对比数据数量")
    logger.info("=" * 60)
    
    for table_name in tables_to_verify:
        logger.info(f"\n📊 验证表: {table_name}")
        
        # 获取 DuckDB 记录数
        duckdb_count = get_table_count(duckdb_conn, table_name, "duckdb")
        logger.info(f"   DuckDB: {duckdb_count:,} 条")
        
        # 检查表是否在 PostgreSQL 中存在
        if table_name not in pg_tables:
            logger.warning(f"   ⚠️  PostgreSQL 中不存在表 {table_name}")
            missing_in_pg.append(table_name)
            results[table_name] = {
                "duckdb_count": duckdb_count,
                "postgresql_count": -1,
                "match": False,
                "status": "missing_in_pg"
            }
            all_match = False
            continue
        
        # 获取 PostgreSQL 记录数
        pg_count = get_table_count(pg_conn, table_name, "postgresql")
        logger.info(f"   PostgreSQL: {pg_count:,} 条")
        
        # 对比
        match = (duckdb_count == pg_count)
        if match:
            logger.info(f"   ✅ 数据数量一致")
        else:
            logger.error(f"   ❌ 数据数量不一致！差异: {abs(duckdb_count - pg_count):,} 条")
            all_match = False
        
        results[table_name] = {
            "duckdb_count": duckdb_count,
            "postgresql_count": pg_count,
            "match": match,
            "difference": abs(duckdb_count - pg_count) if not match else 0,
            "status": "match" if match else "mismatch"
        }
    
    # 检查 PostgreSQL 中是否有 DuckDB 中没有的表
    for table_name in pg_tables:
        if table_name not in tables_to_verify and table_name not in all_schemas:
            # 可能是系统表或自定义表，检查是否有数据
            pg_count = get_table_count(pg_conn, table_name, "postgresql")
            if pg_count > 0:
                logger.warning(f"   ⚠️  PostgreSQL 中有额外表 {table_name} ({pg_count:,} 条记录)")
    
    # 生成报告
    logger.info("\n" + "=" * 60)
    logger.info("验证结果汇总")
    logger.info("=" * 60)
    
    matched_tables = [t for t, r in results.items() if r.get("match")]
    mismatched_tables = [t for t, r in results.items() if not r.get("match")]
    
    logger.info(f"\n✅ 数据一致的表: {len(matched_tables)} 个")
    if matched_tables:
        total_matched = sum(results[t]["duckdb_count"] for t in matched_tables)
        logger.info(f"   总记录数: {total_matched:,}")
    
    if mismatched_tables:
        logger.error(f"\n❌ 数据不一致的表: {len(mismatched_tables)} 个")
        for table_name in mismatched_tables:
            r = results[table_name]
            if r["status"] == "missing_in_pg":
                logger.error(f"   - {table_name}: PostgreSQL 中不存在")
            else:
                logger.error(f"   - {table_name}: DuckDB={r['duckdb_count']:,}, PostgreSQL={r['postgresql_count']:,}, 差异={r['difference']:,}")
    
    if missing_in_pg:
        logger.warning(f"\n⚠️  PostgreSQL 中缺失的表: {len(missing_in_pg)} 个")
        for table_name in missing_in_pg:
            logger.warning(f"   - {table_name}")
    
    if all_match and not missing_in_pg:
        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有表数据验证通过！迁移成功！")
        logger.info("=" * 60)
    else:
        logger.warning("\n" + "=" * 60)
        logger.warning("⚠️  部分表数据不一致，请检查！")
        logger.info("=" * 60)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "all_match": all_match,
        "matched_tables": len(matched_tables),
        "mismatched_tables": len(mismatched_tables),
        "missing_in_pg": len(missing_in_pg),
        "results": results
    }


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("数据迁移验证工具")
    logger.info("=" * 60)
    
    # 加载配置
    try:
        duckdb_conf = load_duckdb_conf()
        duckdb_path = duckdb_conf['db_path']
        pg_config = load_pg_config()
        
        logger.info("\n📝 配置信息:")
        logger.info(f"   DuckDB: {duckdb_path}")
        logger.info(f"   PostgreSQL: {pg_config['host']}:{pg_config['port']}/{pg_config['database']}")
        
    except Exception as e:
        logger.error(f"❌ 加载配置失败: {e}")
        sys.exit(1)
    
    # 连接数据库
    duckdb_conn = None
    pg_conn = None
    
    try:
        # 连接 DuckDB
        if not Path(duckdb_path).exists():
            raise FileNotFoundError(f"DuckDB 数据库文件不存在: {duckdb_path}")
        
        duckdb_conn = duckdb.connect(duckdb_path, read_only=True)
        logger.info(f"✅ DuckDB 连接成功")
        
        # 连接 PostgreSQL
        pg_conn = psycopg2.connect(
            host=pg_config["host"],
            port=pg_config["port"],
            database=pg_config["database"],
            user=pg_config["user"],
            password=pg_config["password"]
        )
        logger.info(f"✅ PostgreSQL 连接成功")
        
        # Schema 管理器
        schema_manager = DbSchemaManager(is_verbose=False)
        
        # 验证数据
        report = verify_tables(duckdb_conn, pg_conn, schema_manager)
        
        # 保存验证报告
        report_file = project_root / "migration_verification_report.json"
        with report_file.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📄 验证报告已保存: {report_file}")
        
        # 返回退出码
        if report["all_match"] and report["missing_in_pg"] == 0:
            sys.exit(0)
        else:
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if duckdb_conn:
            duckdb_conn.close()
        if pg_conn:
            pg_conn.close()


if __name__ == "__main__":
    main()
