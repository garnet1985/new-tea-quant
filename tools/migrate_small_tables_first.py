#!/usr/bin/env python3
"""
分阶段迁移脚本：先迁移小表，最后迁移 stock_kline

使用方法：
    python3 tools/migrate_small_tables_first.py
"""
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.migrate_duckdb_to_postgresql import DataMigrator, load_pg_config
from core.config.loaders.db_conf import load_duckdb_conf


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("分阶段数据迁移：先小表，后 stock_kline")
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
    
    # 设置批量大小
    # 小表使用默认批量大小（10000）
    # stock_kline 使用 1000000（100万条）
    batch_sizes = {
        'stock_kline': 1000000
    }
    
    # 创建迁移器
    migrator = DataMigrator(
        duckdb_path=duckdb_path,
        pg_config=pg_config,
        batch_size=10000,  # 小表默认批量大小
        batch_sizes=batch_sizes
    )
    
    try:
        # 连接数据库
        migrator.connect()
        
        # 执行迁移（排除 stock_kline，会最后迁移）
        results = migrator.migrate_all(
            tables=None,  # 迁移所有表
            exclude_tables=['stock_kline']  # 先不迁移 stock_kline
        )
        
        # 保存迁移报告
        from datetime import datetime
        import json
        
        report_file = project_root / "migration_report.json"
        with report_file.open("w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "duckdb_path": duckdb_path,
                "postgresql_database": pg_config["database"],
                "batch_sizes": batch_sizes,
                "results": results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📄 迁移报告已保存: {report_file}")
        
        # 显示总结
        total_rows = sum(r.get("rows", 0) for r in results.get("results", []))
        successful = results.get("successful_tables", 0)
        failed = results.get("failed_tables", 0)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 小表迁移完成！")
        logger.info(f"   成功: {successful} 个表")
        logger.info(f"   失败: {failed} 个表")
        logger.info(f"   总记录数: {total_rows:,}")
        logger.info("=" * 60)
        
        if failed == 0:
            logger.info("\n🎯 下一步：迁移 stock_kline 表")
            logger.info("   运行: python3 tools/migrate_duckdb_to_postgresql.py --tables stock_kline --kline-batch-size 1000000")
        else:
            logger.warning("\n⚠️  有表迁移失败，请检查错误信息")
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        migrator.close()


if __name__ == "__main__":
    main()
