#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 MySQL 和 DuckDB 数据完整性

使用方法：
    python tools/verify_migration.py [--table TABLE_NAME]
"""
import sys
from pathlib import Path
import pymysql
import duckdb
import json
import argparse

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.infra.db.db_config_manager import DB_CONFIG
from core.config.loaders.db_conf import DUCKDB_CONF


def verify_tables(table_names=None):
    """验证表的记录数"""
    # 连接 MySQL
    mysql_config = DB_CONFIG['base']
    mysql_conn = pymysql.connect(
        host=mysql_config['host'],
        user=mysql_config['user'],
        password=mysql_config['password'],
        database=mysql_config['database'],
        port=mysql_config['port'],
        charset=mysql_config['charset'],
        cursorclass=pymysql.cursors.DictCursor
    )
    
    # 连接 DuckDB
    duckdb_path = DUCKDB_CONF['db_path']
    try:
        duckdb_conn = duckdb.connect(duckdb_path)
    except Exception as e:
        print(f"❌ 无法连接 DuckDB: {e}")
        print("   提示: 请关闭 DBeaver 或其他正在使用 DuckDB 的程序")
        mysql_conn.close()
        return
    
    # 默认验证所有表
    if table_names is None:
        table_names = [
            'stock_list', 'meta_info', 'tag_definition', 'tag_scenario',
            'adj_factor_event', 'gdp', 'lpr', 'shibor', 'corporate_finance',
            'price_indexes', 'investment_trades', 'investment_operations',
            'tag_value', 'system_cache', 'stock_index_indicator',
            'stock_index_indicator_weight', 'stock_kline'
        ]
    
    print("=" * 70)
    print("数据完整性验证")
    print("=" * 70)
    print(f"{'表名':<35} {'MySQL':>12} {'DuckDB':>12} {'状态':>10}")
    print("-" * 70)
    
    all_match = True
    total_mysql = 0
    total_duckdb = 0
    
    for table in table_names:
        try:
            # MySQL 记录数
            with mysql_conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) as count FROM `{table}`")
                mysql_count = cursor.fetchone()['count']
            
            # DuckDB 记录数
            duckdb_count = duckdb_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            
            match = mysql_count == duckdb_count
            status = "✅ 一致" if match else "❌ 不一致"
            
            print(f"{table:<35} {mysql_count:>12,} {duckdb_count:>12,} {status:>10}")
            
            total_mysql += mysql_count
            total_duckdb += duckdb_count
            
            if not match:
                all_match = False
                diff = abs(mysql_count - duckdb_count)
                print(f"  ⚠️  差异: {diff:,} 条记录")
        
        except Exception as e:
            print(f"{table:<35} {'ERROR':>12} {'ERROR':>12} {'❌ 错误':>10}")
            print(f"  ⚠️  {e}")
            all_match = False
    
    print("-" * 70)
    print(f"{'总计':<35} {total_mysql:>12,} {total_duckdb:>12,} {'✅ 一致' if all_match else '❌ 不一致':>10}")
    print("=" * 70)
    
    if all_match:
        print("✅ 所有表数据一致！")
    else:
        print("❌ 部分表数据不一致，需要重新迁移")
    
    mysql_conn.close()
    duckdb_conn.close()


def main():
    parser = argparse.ArgumentParser(description='验证 MySQL 和 DuckDB 数据完整性')
    parser.add_argument('--table', type=str, help='只验证指定表（可多次指定）', action='append')
    
    args = parser.parse_args()
    table_names = args.table if args.table else None
    
    verify_tables(table_names)


if __name__ == '__main__':
    main()
