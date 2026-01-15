#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移 stock_kline 表中缺失的数据

找出 MySQL 中存在但 DuckDB 中不存在的记录，并迁移
"""
import sys
from pathlib import Path
import pymysql
import duckdb
import json
from loguru import logger
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.infra.db.db_config_manager import DB_CONFIG
from core.config.loaders.db_conf import DUCKDB_CONF


class MissingDataMigrator:
    """缺失数据迁移器"""
    
    def __init__(self, batch_size: int = 100000):
        """
        初始化迁移器
        
        Args:
            batch_size: 每批迁移的行数
        """
        self.batch_size = batch_size
        
        # 连接 MySQL
        mysql_config = DB_CONFIG['base']
        self.mysql_conn = pymysql.connect(
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
        self.duckdb_conn = duckdb.connect(duckdb_path)
        
        logger.info(f"✅ 已连接 MySQL: {mysql_config['database']}")
        logger.info(f"✅ 已连接 DuckDB: {duckdb_path}")
    
    def convert_row_to_duckdb(self, row: dict) -> dict:
        """转换单行数据为 DuckDB 格式"""
        converted = {}
        
        for key, value in row.items():
            if value is None:
                converted[key] = None
            elif isinstance(value, datetime):
                converted[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, (int, float)):
                import math
                if isinstance(value, float) and math.isnan(value):
                    converted[key] = None
                else:
                    converted[key] = value
            elif isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                converted[key] = value
            else:
                converted[key] = value
        
        return converted
    
    def find_and_migrate_missing(self):
        """找出并迁移缺失的数据"""
        logger.info("🔍 开始查找缺失的数据...")
        
        # 方法1：使用 NOT EXISTS 查询找出缺失的记录（分批处理）
        # 由于数据量大，我们按主键范围分批查询
        
        # 先获取所有股票ID列表
        logger.info("📊 获取所有股票ID列表...")
        with self.mysql_conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT id FROM stock_kline ORDER BY id")
            stock_ids = [row['id'] for row in cursor.fetchall()]
        
        logger.info(f"   共 {len(stock_ids)} 只股票")
        
        total_migrated = 0
        total_missing = 0
        
        # 按股票分批处理
        for idx, stock_id in enumerate(stock_ids, 1):
            if idx % 100 == 0:
                logger.info(f"   处理进度: {idx}/{len(stock_ids)} 只股票")
            
            # 找出这只股票在 MySQL 中存在但 DuckDB 中不存在的记录
            missing_query = """
                SELECT k.*
                FROM stock_kline k
                WHERE k.id = %s
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM (
                          SELECT id, term, date 
                          FROM read_parquet('data/stocks.duckdb') 
                          WHERE id = ?
                      ) d
                      WHERE d.id = k.id 
                        AND d.term = k.term 
                        AND d.date = k.date
                  )
                LIMIT %s
            """
            
            # 改用更简单的方法：直接查询 MySQL，然后检查每条记录是否在 DuckDB 中存在
            # 先获取这只股票的所有记录
            with self.mysql_conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM stock_kline WHERE id = %s ORDER BY term, date",
                    (stock_id,)
                )
                mysql_rows = cursor.fetchall()
            
            # 检查哪些记录在 DuckDB 中不存在
            missing_rows = []
            for row in mysql_rows:
                check_query = """
                    SELECT COUNT(*) 
                    FROM stock_kline 
                    WHERE id = ? AND term = ? AND date = ?
                """
                count = self.duckdb_conn.execute(
                    check_query,
                    (row['id'], row['term'], row['date'])
                ).fetchone()[0]
                
                if count == 0:
                    missing_rows.append(row)
            
            if not missing_rows:
                continue
            
            total_missing += len(missing_rows)
            logger.info(
                f"  📦 {stock_id}: 缺失 {len(missing_rows)} 条记录 "
                f"(MySQL: {len(mysql_rows)}, DuckDB: {len(mysql_rows) - len(missing_rows)})"
            )
            
            # 批量插入缺失的记录
            if missing_rows:
                converted_rows = [self.convert_row_to_duckdb(row) for row in missing_rows]
                
                # 分批插入
                for i in range(0, len(converted_rows), self.batch_size):
                    batch = converted_rows[i:i + self.batch_size]
                    
                    columns = list(batch[0].keys())
                    placeholders = ', '.join(['?' for _ in columns])
                    insert_query = f"INSERT INTO stock_kline ({', '.join(columns)}) VALUES ({placeholders})"
                    
                    values = [tuple(row[col] for col in columns) for row in batch]
                    for val in values:
                        self.duckdb_conn.execute(insert_query, val)
                    
                    total_migrated += len(batch)
                    
                    if (i + len(batch)) % 50000 == 0:
                        logger.info(f"    已迁移 {total_migrated:,} 条缺失记录...")
        
        logger.info(f"✅ 完成！共迁移 {total_migrated:,} 条缺失记录")
        
        # 验证
        mysql_count = self.mysql_conn.cursor().execute("SELECT COUNT(*) FROM stock_kline").fetchone()['count']
        duckdb_count = self.duckdb_conn.execute("SELECT COUNT(*) FROM stock_kline").fetchone()[0]
        
        logger.info(f"📊 最终统计: MySQL={mysql_count:,}, DuckDB={duckdb_count:,}, 差异={abs(mysql_count - duckdb_count):,}")
        
        return total_migrated
    
    def find_and_migrate_missing_optimized(self):
        """
        优化版本：使用主键游标从MySQL分批读取，批量检查并插入缺失记录
        """
        logger.info("🔍 开始查找缺失的数据（优化版本）...")
        
        # 先获取 MySQL 总记录数
        with self.mysql_conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM stock_kline")
            total_mysql = cursor.fetchone()['count']
        
        logger.info(f"📊 MySQL 总记录数: {total_mysql:,}")
        
        # 获取 DuckDB 当前记录数
        duckdb_count = self.duckdb_conn.execute("SELECT COUNT(*) FROM stock_kline").fetchone()[0]
        logger.info(f"📊 DuckDB 当前记录数: {duckdb_count:,}")
        logger.info(f"📊 预计缺失记录数: {total_mysql - duckdb_count:,}")
        
        # 主键字段
        primary_keys = ['id', 'term', 'date']
        
        # 使用主键游标分批从 MySQL 读取
        total_migrated = 0
        last_key = None
        batch_num = 0
        
        while True:
            batch_num += 1
            
            # 构建查询条件（使用复合主键比较）
            if last_key and all(pk in last_key for pk in primary_keys):
                # 使用 MySQL 的元组比较语法：WHERE (id, term, date) > (?, ?, ?)
                pk_cols = ', '.join([f'`{pk}`' for pk in primary_keys])
                pk_placeholders = ', '.join(['%s'] * len(primary_keys))
                where_clause = f"({pk_cols}) > ({pk_placeholders})"
                query_params = tuple(last_key[pk] for pk in primary_keys)
            else:
                where_clause = "1=1"
                query_params = ()
            
            # 查询一批数据
            order_by = ', '.join([f'`{pk}`' for pk in primary_keys])
            query = f"""
                SELECT * FROM `stock_kline`
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT %s
            """
            
            with self.mysql_conn.cursor() as cursor:
                cursor.execute(query, query_params + (self.batch_size,))
                mysql_rows = cursor.fetchall()
            
            if not mysql_rows:
                break
            
            # 批量检查哪些记录在 DuckDB 中不存在
            # 先构建这批记录的主键集合
            mysql_keys = [(row['id'], row['term'], row['date']) for row in mysql_rows]
            
            # 批量查询 DuckDB 中已存在的记录
            # 使用 IN 子句批量检查（但 DuckDB 的 IN 可能有限制，所以分批检查）
            existing_keys = set()
            check_batch_size = 10000  # 每次检查 10000 条
            
            for i in range(0, len(mysql_keys), check_batch_size):
                batch_keys = mysql_keys[i:i + check_batch_size]
                
                # 构建 IN 查询（使用元组）
                # 注意：DuckDB 支持 (id, term, date) IN ((?, ?, ?), ...) 语法
                placeholders = ', '.join(['(?, ?, ?)'] * len(batch_keys))
                check_query = f"""
                    SELECT id, term, date 
                    FROM stock_kline 
                    WHERE (id, term, date) IN ({placeholders})
                """
                
                # 展开参数
                params = []
                for key in batch_keys:
                    params.extend(key)
                
                for row in self.duckdb_conn.execute(check_query, params).fetchall():
                    existing_keys.add((row[0], row[1], row[2]))
            
            # 找出缺失的记录
            missing_rows = []
            for row in mysql_rows:
                key = (row['id'], row['term'], row['date'])
                if key not in existing_keys:
                    missing_rows.append(row)
            
            # 批量插入缺失的记录
            if missing_rows:
                converted_rows = [self.convert_row_to_duckdb(row) for row in missing_rows]
                
                columns = list(converted_rows[0].keys())
                placeholders = ', '.join(['?' for _ in columns])
                insert_query = f"INSERT INTO stock_kline ({', '.join(columns)}) VALUES ({placeholders})"
                
                # 逐条插入（DuckDB 的 executemany 可能不支持）
                for row in converted_rows:
                    values = tuple(row[col] for col in columns)
                    self.duckdb_conn.execute(insert_query, values)
                
                total_migrated += len(missing_rows)
            
            # 记录最后一条的主键值
            last_row = mysql_rows[-1]
            last_key = {pk: last_row[pk] for pk in primary_keys}
            
            # 显示进度
            if batch_num % 10 == 0 or missing_rows:
                logger.info(
                    f"  批次 {batch_num}: 本批 {len(mysql_rows)} 条, "
                    f"缺失 {len(missing_rows)} 条, "
                    f"累计已迁移 {total_migrated:,} 条"
                )
        
        logger.info(f"✅ 完成！共迁移 {total_migrated:,} 条缺失记录")
        
        # 最终验证
        with self.mysql_conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM stock_kline")
            mysql_count = cursor.fetchone()['count']
        
        final_duckdb_count = self.duckdb_conn.execute("SELECT COUNT(*) FROM stock_kline").fetchone()[0]
        
        logger.info(f"📊 最终统计: MySQL={mysql_count:,}, DuckDB={final_duckdb_count:,}, 差异={abs(mysql_count - final_duckdb_count):,}")
        
        return total_migrated
    
    def close(self):
        """关闭连接"""
        if self.mysql_conn:
            self.mysql_conn.close()
        if self.duckdb_conn:
            self.duckdb_conn.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='迁移 stock_kline 表中缺失的数据')
    parser.add_argument('--batch-size', type=int, default=100000, help='每批迁移的行数（默认: 100000）')
    
    args = parser.parse_args()
    
    migrator = MissingDataMigrator(batch_size=args.batch_size)
    
    try:
        # 使用优化版本
        migrator.find_and_migrate_missing_optimized()
    finally:
        migrator.close()


if __name__ == '__main__':
    main()
