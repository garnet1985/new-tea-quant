#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比 MySQL 和 DuckDB 中 stock_kline 表的差异

找出哪些数据缺失了
"""
import sys
from pathlib import Path
import pymysql
import duckdb
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.infra.db.db_config_manager import DB_CONFIG
from core.config.loaders.db_conf import DUCKDB_CONF


def find_missing_data():
    """找出缺失的数据"""
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
    duckdb_conn = duckdb.connect(duckdb_path)
    
    print("=" * 70)
    print("查找 stock_kline 表的数据差异")
    print("=" * 70)
    
    # 1. 按股票ID统计
    print("\n1. 按股票ID统计记录数（前20个差异最大的）:")
    print("-" * 70)
    
    mysql_query = """
        SELECT id, COUNT(*) as count 
        FROM stock_kline 
        GROUP BY id 
        ORDER BY count DESC
    """
    
    duckdb_query = """
        SELECT id, COUNT(*) as count 
        FROM stock_kline 
        GROUP BY id 
        ORDER BY count DESC
    """
    
    with mysql_conn.cursor() as cursor:
        cursor.execute(mysql_query)
        mysql_by_id = {row['id']: row['count'] for row in cursor.fetchall()}
    
    duckdb_by_id = {}
    for row in duckdb_conn.execute(duckdb_query).fetchall():
        duckdb_by_id[row[0]] = row[1]
    
    # 找出差异
    all_ids = set(mysql_by_id.keys()) | set(duckdb_by_id.keys())
    diffs = []
    for stock_id in all_ids:
        mysql_count = mysql_by_id.get(stock_id, 0)
        duckdb_count = duckdb_by_id.get(stock_id, 0)
        diff = mysql_count - duckdb_count
        if diff != 0:
            diffs.append((stock_id, mysql_count, duckdb_count, diff))
    
    diffs.sort(key=lambda x: abs(x[3]), reverse=True)
    
    print(f"{'股票ID':<20} {'MySQL':>12} {'DuckDB':>12} {'差异':>12}")
    print("-" * 70)
    for stock_id, mysql_count, duckdb_count, diff in diffs[:20]:
        print(f"{stock_id:<20} {mysql_count:>12,} {duckdb_count:>12,} {diff:>12,}")
    
    if len(diffs) > 20:
        print(f"... 还有 {len(diffs) - 20} 只股票有差异")
    
    # 2. 按日期范围统计
    print("\n2. 按日期范围统计记录数:")
    print("-" * 70)
    
    mysql_query = """
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as count
        FROM stock_kline
    """
    
    duckdb_query = """
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as count
        FROM stock_kline
    """
    
    with mysql_conn.cursor() as cursor:
        cursor.execute(mysql_query)
        mysql_date_range = cursor.fetchone()
    
    duckdb_date_range = duckdb_conn.execute(duckdb_query).fetchone()
    
    print(f"MySQL:  日期范围 {mysql_date_range['min_date']} ~ {mysql_date_range['max_date']}, 记录数: {mysql_date_range['count']:,}")
    print(f"DuckDB: 日期范围 {duckdb_date_range[0]} ~ {duckdb_date_range[1]}, 记录数: {duckdb_date_range[2]:,}")
    
    # 3. 按 term 统计
    print("\n3. 按周期(term)统计记录数:")
    print("-" * 70)
    
    mysql_query = """
        SELECT term, COUNT(*) as count 
        FROM stock_kline 
        GROUP BY term 
        ORDER BY term
    """
    
    duckdb_query = """
        SELECT term, COUNT(*) as count 
        FROM stock_kline 
        GROUP BY term 
        ORDER BY term
    """
    
    with mysql_conn.cursor() as cursor:
        cursor.execute(mysql_query)
        mysql_by_term = {row['term']: row['count'] for row in cursor.fetchall()}
    
    duckdb_by_term = {}
    for row in duckdb_conn.execute(duckdb_query).fetchall():
        duckdb_by_term[row[0]] = row[1]
    
    print(f"{'周期':<20} {'MySQL':>12} {'DuckDB':>12} {'差异':>12}")
    print("-" * 70)
    all_terms = set(mysql_by_term.keys()) | set(duckdb_by_term.keys())
    for term in sorted(all_terms):
        mysql_count = mysql_by_term.get(term, 0)
        duckdb_count = duckdb_by_term.get(term, 0)
        diff = mysql_count - duckdb_count
        status = "✅" if diff == 0 else "❌"
        print(f"{status} {term:<18} {mysql_count:>12,} {duckdb_count:>12,} {diff:>12,}")
    
    # 4. 找出具体缺失的记录（采样）
    print("\n4. 采样检查：找出 MySQL 中存在但 DuckDB 中不存在的记录（前10条）:")
    print("-" * 70)
    
    # 随机采样一些记录，检查是否在 DuckDB 中存在
    sample_query = """
        SELECT id, term, date 
        FROM stock_kline 
        ORDER BY RAND() 
        LIMIT 100
    """
    
    with mysql_conn.cursor() as cursor:
        cursor.execute(sample_query)
        samples = cursor.fetchall()
    
    missing_samples = []
    for sample in samples:
        check_query = """
            SELECT COUNT(*) 
            FROM stock_kline 
            WHERE id = ? AND term = ? AND date = ?
        """
        count = duckdb_conn.execute(
            check_query, 
            (sample['id'], sample['term'], sample['date'])
        ).fetchone()[0]
        
        if count == 0:
            missing_samples.append(sample)
            if len(missing_samples) >= 10:
                break
    
    if missing_samples:
        print("缺失的记录示例:")
        for sample in missing_samples:
            print(f"  {sample['id']} | {sample['term']} | {sample['date']}")
    else:
        print("✅ 采样的记录都在 DuckDB 中存在")
    
    # 5. 检查是否有重复主键
    print("\n5. 检查 DuckDB 中是否有重复主键:")
    print("-" * 70)
    
    dup_query = """
        SELECT id, term, date, COUNT(*) as cnt
        FROM stock_kline
        GROUP BY id, term, date
        HAVING COUNT(*) > 1
        LIMIT 10
    """
    
    dups = duckdb_conn.execute(dup_query).fetchall()
    if dups:
        print("发现重复主键:")
        for dup in dups:
            print(f"  {dup[0]} | {dup[1]} | {dup[2]} | 出现 {dup[3]} 次")
    else:
        print("✅ 没有重复主键")
    
    print("\n" + "=" * 70)
    
    mysql_conn.close()
    duckdb_conn.close()


if __name__ == '__main__':
    find_missing_data()
