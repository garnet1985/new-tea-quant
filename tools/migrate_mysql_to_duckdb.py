#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 到 DuckDB 数据迁移脚本

功能：
- 从 MySQL 分批导出数据
- 转换数据格式（日期、浮点数、JSON等）
- 批量导入到 DuckDB
- 支持断点续传
- 数据完整性验证

使用方法：
    python tools/migrate_mysql_to_duckdb.py [--table TABLE_NAME] [--batch-size SIZE] [--insert-batch-size SIZE] [--resume] [--all-tables]
    
默认行为：
    - 默认只迁移 stock_kline 表
    - 使用 --table 指定要迁移的表（可多次指定）
    - 使用 --all-tables 迁移所有表
    
参数说明：
    --batch-size: 从 MySQL 读取的每批行数（默认: 100000）
    --insert-batch-size: 插入到 DuckDB 的每批行数（默认: 5000，避免内存占用过大）
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
import pymysql
import duckdb
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.infra.db.db_config_manager import DB_CONFIG
from core.config.loaders.db_conf import DUCKDB_CONF


class MigrationProgress:
    """迁移进度管理器"""
    
    def __init__(self, progress_file: str = "tools/migration_progress.json"):
        self.progress_file = Path(progress_file)
        self.progress = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """加载进度文件"""
        if self.progress_file.exists():
            try:
                with self.progress_file.open('r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载进度文件失败: {e}，将从头开始")
        return {}
    
    def save_progress(self, table_name: str, last_key: Dict, migrated_rows: int):
        """保存进度"""
        if table_name not in self.progress:
            self.progress[table_name] = {}
        
        # 将 last_key 中的日期/时间类型转换为字符串，避免 JSON 序列化错误
        from datetime import date
        serializable_last_key = {}
        for k, v in (last_key or {}).items():
            if isinstance(v, datetime):
                serializable_last_key[k] = v.isoformat()
            elif isinstance(v, date):
                serializable_last_key[k] = v.isoformat()
            else:
                serializable_last_key[k] = v
        
        self.progress[table_name].update({
            'last_key': serializable_last_key,
            'migrated_rows': migrated_rows,
            'updated_at': datetime.now().isoformat()
        })
        
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with self.progress_file.open('w', encoding='utf-8') as f:
            json.dump(self.progress, f, indent=2, ensure_ascii=False)
    
    def get_progress(self, table_name: str) -> Optional[Dict]:
        """获取进度"""
        return self.progress.get(table_name)
    
    def clear_progress(self, table_name: str):
        """清除进度（从头开始）"""
        if table_name in self.progress:
            del self.progress[table_name]
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            with self.progress_file.open('w', encoding='utf-8') as f:
                json.dump(self.progress, f, indent=2, ensure_ascii=False)


class DataMigrator:
    """数据迁移器"""
    
    # 需要迁移的表列表（按依赖顺序）
    TABLES_TO_MIGRATE = [
        # 基础表（无依赖）
        'stock_list',
        'meta_info',
        'tag_definition',
        'tag_scenario',
        # 依赖基础表的表
        'adj_factor_event',
        'stock_kline',  # 大表，最后迁移
        'gdp',
        'lpr',
        'shibor',
        'corporate_finance',
        'price_indexes',
        'investment_trades',
        'investment_operations',
        'tag_value',
        'system_cache',
        'stock_index_indicator',
        'stock_index_indicator_weight',
    ]
    
    def __init__(self, batch_size: int = 100000, resume: bool = True, insert_batch_size: int = 5000):
        """
        初始化迁移器
        
        Args:
            batch_size: 从 MySQL 读取的每批行数（默认 100000）
            resume: 是否支持断点续传
            insert_batch_size: 插入到 DuckDB 的每批行数（默认 5000，避免内存占用过大）
        """
        self.batch_size = batch_size
        self.insert_batch_size = insert_batch_size
        self.resume = resume
        self.progress = MigrationProgress()
        
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
        Path(duckdb_path).parent.mkdir(parents=True, exist_ok=True)
        self.duckdb_conn = duckdb.connect(duckdb_path)
        
        logger.info(f"✅ 已连接 MySQL: {mysql_config['database']}")
        logger.info(f"✅ 已连接 DuckDB: {duckdb_path}")
    
    def get_table_primary_key(self, table_name: str) -> List[str]:
        """获取表的主键字段列表"""
        # 从 schema 文件读取
        schema_path = project_root / 'app' / 'core' / 'modules' / 'data_manager' / 'base_tables' / table_name / 'schema.json'
        
        if schema_path.exists():
            with schema_path.open('r', encoding='utf-8') as f:
                schema = json.load(f)
                pk = schema.get('primaryKey')
                if isinstance(pk, str):
                    return [pk]
                elif isinstance(pk, list):
                    return pk
        
        # 兜底：从数据库查询
        with self.mysql_conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT COLUMN_NAME 
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = %s 
                  AND TABLE_NAME = %s 
                  AND CONSTRAINT_NAME = 'PRIMARY'
                ORDER BY ORDINAL_POSITION
            """, (DB_CONFIG['base']['database'], table_name))
            result = cursor.fetchall()
            return [row['COLUMN_NAME'] for row in result] if result else []
    
    def get_table_count(self, table_name: str) -> int:
        """获取表的记录数"""
        with self.mysql_conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
            return cursor.fetchone()['count']
    
    def convert_row_to_duckdb(self, row: Dict, table_name: str) -> Dict:
        """
        转换单行数据为 DuckDB 格式
        
        主要处理：
        - 日期时间格式
        - 浮点数精度
        - NULL 值
        - JSON 字段
        """
        converted = {}
        
        for key, value in row.items():
            if value is None:
                converted[key] = None
            elif isinstance(value, datetime):
                # MySQL datetime -> DuckDB timestamp
                converted[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, date):
                # MySQL date -> DuckDB date (字符串格式)
                converted[key] = value.strftime('%Y-%m-%d')
            elif isinstance(value, (int, float)):
                # 处理 NaN
                import math
                if isinstance(value, float) and math.isnan(value):
                    converted[key] = None
                else:
                    converted[key] = value
            elif isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                # JSON 字符串，保持原样（DuckDB 支持 JSON 类型）
                converted[key] = value
            else:
                converted[key] = value
        
        return converted
    
    def migrate_table_with_cursor(
        self, 
        table_name: str, 
        primary_keys: List[str],
        start_key: Optional[Dict] = None
    ) -> Tuple[int, Optional[Dict]]:
        """
        使用主键游标分批迁移表数据
        
        Args:
            table_name: 表名
            primary_keys: 主键字段列表
            start_key: 起始主键值（用于断点续传）
        
        Returns:
            (迁移的行数, 最后一条记录的主键值)
        """
        total_migrated = 0
        last_key = start_key
        
        # 构建排序和条件（主键字段统一加反引号，避免保留字冲突，例如 system_cache.key）
        order_by = ', '.join([f'`{pk}`' for pk in primary_keys])
        
        while True:
            # 构建查询条件（使用复合主键比较，MySQL 支持元组比较）
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
            query = f"""
                SELECT * FROM `{table_name}`
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT %s
            """
            
            with self.mysql_conn.cursor() as cursor:
                cursor.execute(query, query_params + (self.batch_size,))
                rows = cursor.fetchall()
            
            if not rows:
                break
            
            # 转换数据格式
            converted_rows = [self.convert_row_to_duckdb(row, table_name) for row in rows]
            logger.debug(f"  🔄 转换了 {len(converted_rows)} 行数据")
            
            # 记录插入的行数（用于验证）
            rows_inserted_this_batch = 0
            
            # 批量插入到 DuckDB（使用批量插入提升性能，分批处理避免内存占用过大）
            if converted_rows:
                logger.debug(f"  📝 开始批量插入，共 {len(converted_rows)} 行，将分为 {(len(converted_rows) + self.insert_batch_size - 1) // self.insert_batch_size} 批")
                columns = list(converted_rows[0].keys())
                columns_sql = ', '.join(columns)
                
                # 批量插入大小（使用实例变量，可配置）
                # 注意：这里的分批是在 converted_rows 基础上的进一步分批
                # converted_rows 本身已经是 batch_size 大小（默认 100000）
                INSERT_BATCH_SIZE = self.insert_batch_size
                
                # 分批处理，每批处理完立即插入并释放内存
                for batch_start in range(0, len(converted_rows), INSERT_BATCH_SIZE):
                    batch_rows = converted_rows[batch_start:batch_start + INSERT_BATCH_SIZE]
                    
                    # 构建当前批次的 VALUES 列表
                    values_list = []
                    for row in batch_rows:
                        row_values = [row[col] for col in columns]
                        # 处理 None 和特殊值
                        formatted_values = []
                        for val in row_values:
                            if val is None:
                                formatted_values.append('NULL')
                            elif isinstance(val, str):
                                # 转义单引号
                                escaped = val.replace("'", "''")
                                formatted_values.append(f"'{escaped}'")
                            elif isinstance(val, (datetime, date)):
                                # 日期时间类型：确保格式化为字符串并加引号
                                if isinstance(val, datetime):
                                    formatted_values.append(f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'")
                                else:
                                    formatted_values.append(f"'{val.strftime('%Y-%m-%d')}'")
                            elif isinstance(val, (int, float)):
                                import math
                                if isinstance(val, float) and math.isnan(val):
                                    formatted_values.append('NULL')
                                else:
                                    formatted_values.append(str(val))
                            elif isinstance(val, bool):
                                formatted_values.append('TRUE' if val else 'FALSE')
                            else:
                                # 其他类型转为字符串并加引号（安全处理）
                                escaped_val = str(val).replace("'", "''")
                                formatted_values.append(f"'{escaped_val}'")
                        values_list.append(f"({', '.join(formatted_values)})")
                    
                    # 执行当前批次的插入
                    if values_list:
                        try:
                            batch_query = f"INSERT INTO {table_name} ({columns_sql}) VALUES {', '.join(values_list)}"
                            
                            # 记录插入前的行数（用于验证）
                            try:
                                count_before = self.duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                            except Exception as count_error:
                                logger.warning(f"  ⚠️ 获取插入前行数失败: {count_error}")
                                count_before = 0
                            
                            # 执行插入
                            logger.debug(f"  🔨 执行插入 (批次 {batch_start}-{batch_start+len(batch_rows)}, SQL 长度: {len(batch_query)})")
                            self.duckdb_conn.execute(batch_query)
                            logger.debug(f"  ✅ INSERT 语句执行完成（未抛出异常）")
                            
                            # 验证插入是否成功
                            try:
                                count_after = self.duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                                actual_inserted = count_after - count_before
                                
                                logger.debug(
                                    f"  📊 插入验证: 前={count_before}, 后={count_after}, "
                                    f"实际插入={actual_inserted}, 期望={len(batch_rows)}"
                                )
                                
                                if actual_inserted != len(batch_rows):
                                    logger.warning(
                                        f"⚠️ 插入行数不匹配 (表: {table_name}, 批次: {batch_start}-{batch_start+len(batch_rows)}): "
                                        f"期望 {len(batch_rows)} 行, 实际插入 {actual_inserted} 行"
                                    )
                                
                                rows_inserted_this_batch += actual_inserted
                                
                                # 每批都记录（用于调试）
                                if actual_inserted > 0:
                                    logger.debug(f"  ✅ 批次 {batch_start}-{batch_start+len(batch_rows)}: 成功插入 {actual_inserted} 行")
                                else:
                                    logger.warning(f"  ⚠️ 批次 {batch_start}-{batch_start+len(batch_rows)}: 插入后行数未增加！")
                                
                                # 每 10 批记录一次进度
                                if (batch_start // INSERT_BATCH_SIZE) % 10 == 0:
                                    logger.info(
                                        f"  📊 {table_name}: 已插入 {rows_inserted_this_batch} 行 "
                                        f"(当前批次: {batch_start}-{batch_start+len(batch_rows)}, 实际插入: {actual_inserted})"
                                    )
                            except Exception as verify_error:
                                logger.error(f"❌ 验证插入结果失败: {verify_error}")
                                import traceback
                                logger.error(f"   详细错误: {traceback.format_exc()}")
                                # 即使验证失败，也假设插入成功（因为 execute 没有抛出异常）
                                rows_inserted_this_batch += len(batch_rows)
                                
                        except Exception as e:
                            logger.error(f"❌ 插入批次失败 (表: {table_name}, 批次: {batch_start}-{batch_start+len(batch_rows)}): {e}")
                            # 打印前几行数据用于调试
                            if batch_rows:
                                logger.error(f"   示例数据（第一行）: {batch_rows[0]}")
                                # 打印 SQL 片段（前 500 字符）用于调试
                                if len(batch_query) > 500:
                                    logger.error(f"   SQL 片段（前500字符）: {batch_query[:500]}...")
                                else:
                                    logger.error(f"   SQL: {batch_query}")
                            import traceback
                            logger.error(f"   详细错误: {traceback.format_exc()}")
                            raise  # 重新抛出异常，让上层处理
                    
                    # 释放内存（Python 会自动回收，但显式删除可以加速）
                    del values_list, batch_rows
                
                # 记录本批次插入的行数
                if rows_inserted_this_batch > 0:
                    logger.info(f"  ✅ 本批次成功插入 {rows_inserted_this_batch} 行到 {table_name}")
                elif len(converted_rows) > 0:
                    logger.error(f"  ❌ 本批次转换了 {len(converted_rows)} 行，但未插入任何数据！")
                    logger.error(f"     这可能表示插入操作失败但没有抛出异常")
            else:
                logger.warning(f"  ⚠️ 转换后的数据为空，跳过插入")
            
            # 记录最后一条的主键值
            last_row = rows[-1]
            last_key = {pk: last_row[pk] for pk in primary_keys}
            
            total_migrated += len(rows)
            
            logger.info(
                f"  📦 {table_name}: 已处理 {total_migrated} 行 "
                f"(本批: {len(rows)} 行, 转换: {len(converted_rows) if 'converted_rows' in locals() else 0} 行, "
                f"插入: {rows_inserted_this_batch} 行, 最后主键: {last_key})"
            )
            
            # 如果插入行数为 0，发出警告
            if rows_inserted_this_batch == 0 and len(rows) > 0:
                logger.error(f"  ❌ 警告：处理了 {len(rows)} 行，但插入行数为 0！")
            
            # 保存进度
            if self.resume:
                self.progress.save_progress(table_name, last_key, total_migrated)
        
        return total_migrated, last_key
    
    def migrate_table(self, table_name: str) -> bool:
        """
        迁移单个表
        
        Returns:
            是否成功
        """
        logger.info(f"🔄 开始迁移表: {table_name}")
        
        try:
            # 检查表是否已有数据
            try:
                existing_count = self.duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                has_existing_data = existing_count > 0
            except:
                existing_count = 0
                has_existing_data = False
            
            # 检查是否有进度文件
            has_progress = False
            if self.resume:
                progress = self.progress.get_progress(table_name)
                if progress and progress.get('last_key'):
                    has_progress = True
            
            # 决定是否清空表和进度
            if has_existing_data or has_progress:
                # 如果表有数据或进度文件存在，清空表并清除进度（从头开始）
                try:
                    self.duckdb_conn.execute(f"DELETE FROM {table_name}")
                    logger.info(f"  🧹 已清空 DuckDB 表 {table_name} 的历史数据（原有 {existing_count:,} 条记录）")
                except Exception as e:
                    logger.warning(f"  ⚠️ 清空 DuckDB 表 {table_name} 失败（可能表不存在或无数据）: {e}")
                
                # 清空进度文件（因为表已清空，进度无效）
                if has_progress:
                    self.progress.clear_progress(table_name)
                    logger.info(f"  🧹 已清除进度文件（因为表已清空，从头开始迁移）")
                    start_key = None
                    start_rows = 0
                else:
                    start_key = None
                    start_rows = 0
            else:
                # 表为空且无进度，检查是否可以断点续传
                if self.resume:
                    progress = self.progress.get_progress(table_name)
                    if progress:
                        start_key = progress.get('last_key')
                        start_rows = progress.get('migrated_rows', 0)
                        if start_key:
                            logger.info(f"  🔄 从断点继续: 已迁移 {start_rows:,} 行，从主键 {start_key} 继续")
                        else:
                            start_key = None
                            start_rows = 0
                    else:
                        start_key = None
                        start_rows = 0
                else:
                    start_key = None
                    start_rows = 0
            
            # 获取主键
            primary_keys = self.get_table_primary_key(table_name)
            if not primary_keys:
                logger.warning(f"⚠️  表 {table_name} 没有主键，使用简单迁移方式")
                return self._migrate_table_simple(table_name)
            
            # 获取总记录数
            total_count = self.get_table_count(table_name)
            logger.info(f"  📊 MySQL 总记录数: {total_count:,}")
            
            # 如果从断点继续，计算剩余记录数
            if start_key:
                remaining = total_count - start_rows
                logger.info(f"  📊 剩余待迁移: {remaining:,} 行（从 {start_rows:,} 行继续）")
            
            # 执行迁移
            start_time = time.time()
            
            # 记录迁移前的记录数（应该在清空后为 0）
            try:
                count_before_migration = self.duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                if count_before_migration > 0:
                    logger.warning(f"  ⚠️ 迁移前 DuckDB 记录数: {count_before_migration:,}（应该为 0，可能清空失败）")
                else:
                    logger.info(f"  📊 迁移前 DuckDB 记录数: {count_before_migration:,}（已清空）")
            except Exception as e:
                logger.warning(f"  ⚠️ 无法获取迁移前记录数: {e}")
                count_before_migration = 0
            
            try:
                migrated_count, _ = self.migrate_table_with_cursor(table_name, primary_keys, start_key)
            except Exception as e:
                logger.error(f"❌ 迁移过程中发生异常: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # 检查当前已插入的记录数
                try:
                    current_count = self.duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    actual_inserted = current_count - count_before_migration
                    logger.error(f"   迁移前: {count_before_migration:,}, 当前: {current_count:,}, 实际插入: {actual_inserted:,}")
                except Exception as count_error:
                    logger.error(f"   无法获取当前记录数: {count_error}")
                raise  # 重新抛出异常
            
            # 验证数据完整性
            duckdb_count = self.duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            elapsed = time.time() - start_time
            logger.info(
                f"✅ 表 {table_name} 迁移完成: "
                f"MySQL={total_count:,}, DuckDB={duckdb_count:,}, "
                f"耗时={elapsed:.2f}秒, 速度={migrated_count/elapsed:.0f} 行/秒"
            )
            
            if total_count != duckdb_count:
                logger.warning(
                    f"⚠️  记录数不一致: MySQL={total_count:,}, DuckDB={duckdb_count:,}, "
                    f"差异={abs(total_count - duckdb_count):,}"
                )
                return False
            
            # 清除进度（迁移完成）
            if self.resume:
                self.progress.clear_progress(table_name)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 迁移表 {table_name} 失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _migrate_table_simple(self, table_name: str) -> bool:
        """简单迁移方式（无主键或主键获取失败时使用）"""
        try:
            total_count = self.get_table_count(table_name)
            logger.info(f"  📊 总记录数: {total_count:,}")
            
            offset = 0
            migrated_count = 0
            start_time = time.time()
            
            while offset < total_count:
                query = f"SELECT * FROM `{table_name}` LIMIT %s OFFSET %s"
                
                with self.mysql_conn.cursor() as cursor:
                    cursor.execute(query, (self.batch_size, offset))
                    rows = cursor.fetchall()
                
                if not rows:
                    break
                
                # 转换并插入
                converted_rows = [self.convert_row_to_duckdb(row, table_name) for row in rows]
                
                if converted_rows:
                    columns = list(converted_rows[0].keys())
                    placeholders = ', '.join(['?' for _ in columns])
                    # 使用批量插入提升性能，分批处理避免内存占用过大
                    columns_sql = ', '.join(columns)
                    INSERT_BATCH_SIZE = self.insert_batch_size
                    
                    # 分批处理，每批处理完立即插入并释放内存
                    for batch_start in range(0, len(converted_rows), INSERT_BATCH_SIZE):
                        batch_rows = converted_rows[batch_start:batch_start + INSERT_BATCH_SIZE]
                        
                        # 构建当前批次的 VALUES 列表
                        values_list = []
                        for row in batch_rows:
                            row_values = [row[col] for col in columns]
                            formatted_values = []
                            for val in row_values:
                                if val is None:
                                    formatted_values.append('NULL')
                                elif isinstance(val, str):
                                    # 转义单引号
                                    escaped = val.replace("'", "''")
                                    formatted_values.append(f"'{escaped}'")
                                elif isinstance(val, (datetime, date)):
                                    # 日期时间类型：确保格式化为字符串并加引号
                                    if isinstance(val, datetime):
                                        formatted_values.append(f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'")
                                    else:
                                        formatted_values.append(f"'{val.strftime('%Y-%m-%d')}'")
                                elif isinstance(val, (int, float)):
                                    import math
                                    if isinstance(val, float) and math.isnan(val):
                                        formatted_values.append('NULL')
                                    else:
                                        formatted_values.append(str(val))
                                elif isinstance(val, bool):
                                    formatted_values.append('TRUE' if val else 'FALSE')
                                else:
                                    # 其他类型转为字符串并加引号（安全处理）
                                    escaped_val = str(val).replace("'", "''")
                                    formatted_values.append(f"'{escaped_val}'")
                            values_list.append(f"({', '.join(formatted_values)})")
                        
                        # 执行当前批次的插入
                        if values_list:
                            batch_query = f"INSERT INTO {table_name} ({columns_sql}) VALUES {', '.join(values_list)}"
                            self.duckdb_conn.execute(batch_query)
                        
                        # 释放内存
                        del values_list, batch_rows
                
                migrated_count += len(rows)
                offset += len(rows)
                
                logger.info(f"  📦 {table_name}: 已迁移 {migrated_count:,}/{total_count:,} 行")
            
            elapsed = time.time() - start_time
            duckdb_count = self.duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            logger.info(
                f"✅ 表 {table_name} 迁移完成: "
                f"MySQL={total_count:,}, DuckDB={duckdb_count:,}, "
                f"耗时={elapsed:.2f}秒"
            )
            
            return total_count == duckdb_count
            
        except Exception as e:
            logger.error(f"❌ 简单迁移表 {table_name} 失败: {e}")
            return False
    
    def migrate_all(self, table_names: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        迁移所有表
        
        Args:
            table_names: 要迁移的表列表，None 表示迁移所有表
        
        Returns:
            {表名: 是否成功}
        """
        if table_names is None:
            table_names = self.TABLES_TO_MIGRATE
        
        results = {}
        start_time = time.time()
        
        logger.info(f"🚀 开始迁移 {len(table_names)} 个表")
        logger.info(f"   批次大小: {self.batch_size:,} 行/批")
        logger.info(f"   断点续传: {'启用' if self.resume else '禁用'}")
        
        for table_name in table_names:
            success = self.migrate_table(table_name)
            results[table_name] = success
            
            if not success:
                logger.error(f"❌ 表 {table_name} 迁移失败，但继续迁移其他表")
        
        total_elapsed = time.time() - start_time
        success_count = sum(1 for v in results.values() if v)
        
        logger.info("=" * 60)
        logger.info(f"📊 迁移完成: {success_count}/{len(table_names)} 个表成功")
        logger.info(f"⏱️  总耗时: {total_elapsed:.2f} 秒 ({total_elapsed/60:.1f} 分钟)")
        logger.info("=" * 60)
        
        return results
    
    def close(self):
        """关闭连接"""
        if self.mysql_conn:
            self.mysql_conn.close()
        if self.duckdb_conn:
            self.duckdb_conn.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MySQL 到 DuckDB 数据迁移工具')
    parser.add_argument('--table', type=str, help='只迁移指定表（可多次指定）。默认只迁移 stock_kline', action='append')
    parser.add_argument('--all-tables', action='store_true', help='迁移所有表（默认只迁移 stock_kline）')
    parser.add_argument('--batch-size', type=int, default=100000, 
                       help='从 MySQL 读取的每批行数（默认: 100000）')
    parser.add_argument('--insert-batch-size', type=int, default=5000,
                       help='插入到 DuckDB 的每批行数（默认: 5000，避免内存占用过大）')
    parser.add_argument('--no-resume', action='store_true', help='禁用断点续传（从头开始）')
    parser.add_argument('--clear-progress', type=str, help='清除指定表的进度（从头开始）')
    
    args = parser.parse_args()
    
    # 清除进度
    if args.clear_progress:
        progress = MigrationProgress()
        progress.clear_progress(args.clear_progress)
        logger.info(f"✅ 已清除表 {args.clear_progress} 的进度")
        return
    
    # 创建迁移器
    migrator = DataMigrator(
        batch_size=args.batch_size,
        resume=not args.no_resume,
        insert_batch_size=args.insert_batch_size
    )
    
    try:
        # 执行迁移
        # 确定要迁移的表
        if args.table:
            # 用户指定了表
            table_names = args.table
        elif args.all_tables:
            # 用户要求迁移所有表
            table_names = None
        else:
            # 默认只迁移 stock_kline
            table_names = ['stock_kline']
            logger.info("ℹ️  默认只迁移 stock_kline 表，使用 --all-tables 迁移所有表")
        
        results = migrator.migrate_all(table_names)
        
        # 输出结果摘要
        failed_tables = [name for name, success in results.items() if not success]
        if failed_tables:
            logger.error(f"❌ 以下表迁移失败: {', '.join(failed_tables)}")
            sys.exit(1)
        else:
            logger.info("✅ 所有表迁移成功！")
    
    finally:
        migrator.close()


if __name__ == '__main__':
    main()
