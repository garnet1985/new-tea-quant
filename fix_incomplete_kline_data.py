"""
修复stock_kline表中不完整的数据

问题：
- K线数据存在（open, close等有值）
- daily_basic数据缺失（pe, turnoverRate等全是0）
- 原因：daily_basic API失败但数据已入库

解决方案：
- 方案1：删除不完整数据，让renew重新拉取
- 方案2：从日线数据修复周线/月线数据（仅适用weekly/monthly）
"""

import sys
from loguru import logger

# 配置logger
logger.remove()
logger.add(sys.stderr, level="INFO")

from utils.db.db_manager import DatabaseManager


def find_incomplete_records(db: DatabaseManager):
    """
    查找不完整的记录
    
    判断标准：
    - turnoverRate = 0 AND pe = 0 AND pb = 0 (所有basic指标都是0)
    - 说明：正常情况下，至少有一个指标不为0
    
    Returns:
        Dict: {term: count}
    """
    logger.info("=" * 60)
    logger.info("扫描不完整的数据...")
    logger.info("=" * 60)
    
    # 快速采样检测（查询每个term的前100条）
    logger.info("使用采样方式快速检测...")
    
    incomplete_stats = {}
    total_sampled = 0
    
    for term in ['daily', 'weekly', 'monthly']:
        sample_query = f"""
            SELECT COUNT(*) as count
            FROM stock_kline
            WHERE term = '{term}'
              AND turnoverRate = 0 
              AND pe = 0 
              AND pb = 0
              AND totalShare = 0
            LIMIT 1000
        """
        
        try:
            with db.get_sync_cursor() as cursor:
                cursor.execute(sample_query)
                result = cursor.fetchone()
                count = result['count'] if result else 0
                
                if count > 0:
                    incomplete_stats[term] = count
                    total_sampled += count
                    logger.info(f"  - {term:8s}: 至少 {count:4d} 条不完整记录（采样）")
        except Exception as e:
            logger.error(f"  - {term:8s}: 查询失败 ({e})")
    
    if total_sampled == 0:
        logger.info("\n  ✅ 未发现不完整数据（采样检测）")
    else:
        logger.warning(f"\n  ⚠️  发现至少 {total_sampled} 条不完整记录（采样1000条/term）")
        logger.info("  实际数量可能更多，建议执行修复")
    
    return incomplete_stats, total_sampled


def delete_incomplete_records(db: DatabaseManager, term: str = None, limit: int = None):
    """
    删除不完整的记录
    
    Args:
        db: 数据库管理器
        term: 指定term（daily/weekly/monthly），None表示所有
        limit: 限制删除数量（用于测试），None表示不限制
    """
    logger.info("\n" + "=" * 60)
    logger.info("删除不完整的数据...")
    logger.info("=" * 60)
    
    # 构建WHERE条件
    where_conditions = [
        "turnoverRate = 0",
        "pe = 0",
        "pb = 0",
        "totalShare = 0"
    ]
    
    if term:
        where_conditions.append(f"term = '{term}'")
    
    where_clause = " AND ".join(where_conditions)
    
    # 先查询要删除的数据统计
    query = f"""
        SELECT term, COUNT(*) as count, COUNT(DISTINCT id) as stock_count
        FROM stock_kline
        WHERE {where_clause}
        GROUP BY term
    """
    
    with db.get_sync_cursor() as cursor:
        cursor.execute(query)
        stats = cursor.fetchall()
    
    logger.info(f"即将删除的数据:")
    for row in stats:
        logger.info(f"  - {row['term']:8s}: {row['count']:6d} 条记录，涉及 {row['stock_count']:4d} 只股票")
    
    # 执行删除
    delete_query = f"DELETE FROM stock_kline WHERE {where_clause}"
    if limit:
        delete_query += f" LIMIT {limit}"
    
    logger.warning(f"\n⚠️  准备执行删除...")
    logger.warning(f"SQL: {delete_query}")
    
    # 需要用户确认
    if not limit:
        confirm = input("\n确认删除？(yes/no): ")
        if confirm.lower() != 'yes':
            logger.info("❌ 取消删除操作")
            return
    
    with db.get_sync_cursor() as cursor:
        affected = cursor.execute(delete_query)
        cursor.connection.commit()
    
    logger.success(f"✅ 删除完成！共删除 {affected} 条记录")


def fix_weekly_monthly_from_daily(db: DatabaseManager, term: str, limit: int = None):
    """
    从日线数据修复周线/月线的basic字段
    
    原理：
    - 周线/月线的日期对应某个交易日
    - 从日线数据中查找同一天的basic指标
    - 更新到周线/月线
    
    Args:
        db: 数据库管理器
        term: 'weekly' 或 'monthly'
        limit: 限制修复数量（用于测试）
    """
    if term not in ['weekly', 'monthly']:
        logger.error(f"❌ 仅支持修复weekly/monthly，不支持: {term}")
        return
    
    logger.info("\n" + "=" * 60)
    logger.info(f"从日线数据修复 {term} 的basic字段...")
    logger.info("=" * 60)
    
    # 查询需要修复的记录
    query = f"""
        SELECT id, date, term
        FROM stock_kline
        WHERE term = '{term}'
          AND turnoverRate = 0
          AND pe = 0
          AND pb = 0
          AND totalShare = 0
        {f'LIMIT {limit}' if limit else ''}
    """
    
    with db.get_sync_cursor() as cursor:
        cursor.execute(query)
        incomplete_records = cursor.fetchall()
    
    logger.info(f"找到 {len(incomplete_records)} 条需要修复的{term}记录")
    
    if not incomplete_records:
        logger.info("✅ 没有需要修复的数据")
        return
    
    # 显示前5条示例
    logger.info("\n示例记录（前5条）:")
    for i, record in enumerate(incomplete_records[:5]):
        logger.info(f"  {i+1}. {record['id']} {record['date']}")
    
    # 需要用户确认
    if not limit or len(incomplete_records) > 10:
        confirm = input(f"\n确认修复 {len(incomplete_records)} 条记录？(yes/no): ")
        if confirm.lower() != 'yes':
            logger.info("❌ 取消修复操作")
            return
    
    # 批量修复
    fixed_count = 0
    failed_count = 0
    
    logger.info(f"\n🔄 开始修复...")
    
    for i, record in enumerate(incomplete_records):
        stock_id = record['id']
        date = record['date']
        
        try:
            # 从日线数据中查找对应日期的basic指标
            daily_query = """
                SELECT turnoverRate, freeTurnoverRate, volumeRatio,
                       pe, peTTM, pb, ps, psTTM,
                       dvRatio, dvTTM,
                       totalShare, floatShare, freeShare,
                       totalMarketValue, circMarketValue
                FROM stock_kline
                WHERE id = %s AND date = %s AND term = 'daily'
                LIMIT 1
            """
            
            with db.get_sync_cursor() as cursor:
                cursor.execute(daily_query, (stock_id, date))
                daily_data = cursor.fetchone()
            
            if not daily_data:
                logger.debug(f"  {i+1:4d}. {stock_id} {date} - ❌ 未找到对应日线数据")
                failed_count += 1
                continue
            
            # 检查日线数据是否完整
            if daily_data['pe'] == 0 and daily_data['pb'] == 0 and daily_data['totalShare'] == 0:
                logger.debug(f"  {i+1:4d}. {stock_id} {date} - ⚠️  日线数据也不完整，跳过")
                failed_count += 1
                continue
            
            # 更新周线/月线数据
            update_query = f"""
                UPDATE stock_kline
                SET turnoverRate = %s,
                    freeTurnoverRate = %s,
                    volumeRatio = %s,
                    pe = %s,
                    peTTM = %s,
                    pb = %s,
                    ps = %s,
                    psTTM = %s,
                    dvRatio = %s,
                    dvTTM = %s,
                    totalShare = %s,
                    floatShare = %s,
                    freeShare = %s,
                    totalMarketValue = %s,
                    circMarketValue = %s
                WHERE id = %s AND date = %s AND term = %s
            """
            
            params = (
                daily_data['turnoverRate'],
                daily_data['freeTurnoverRate'],
                daily_data['volumeRatio'],
                daily_data['pe'],
                daily_data['peTTM'],
                daily_data['pb'],
                daily_data['ps'],
                daily_data['psTTM'],
                daily_data['dvRatio'],
                daily_data['dvTTM'],
                daily_data['totalShare'],
                daily_data['floatShare'],
                daily_data['freeShare'],
                daily_data['totalMarketValue'],
                daily_data['circMarketValue'],
                stock_id,
                date,
                term
            )
            
            with db.get_sync_cursor() as cursor:
                cursor.execute(update_query, params)
                cursor.connection.commit()
            
            fixed_count += 1
            
            if (i + 1) % 100 == 0:
                logger.info(f"  进度: {i+1}/{len(incomplete_records)} ({fixed_count} 修复, {failed_count} 失败)")
        
        except Exception as e:
            logger.error(f"  {i+1:4d}. {stock_id} {date} - ❌ 修复失败: {e}")
            failed_count += 1
    
    logger.info(f"\n📊 修复完成:")
    logger.info(f"  - 成功: {fixed_count} 条")
    logger.info(f"  - 失败: {failed_count} 条")
    logger.success(f"✅ {term} 数据修复完成！")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Stock K-line 数据修复工具")
    logger.info("=" * 60)
    
    # 初始化数据库
    db = DatabaseManager(is_verbose=False, enable_thread_safety=True)
    db.initialize()
    
    # 扫描不完整数据
    incomplete_stats, total_count = find_incomplete_records(db)
    
    if total_count == 0:
        logger.success("\n✅ 没有发现不完整的数据！")
        return
    
    # 显示菜单
    logger.info("\n" + "=" * 60)
    logger.info("选择修复方案:")
    logger.info("=" * 60)
    logger.info("1. 删除所有不完整数据（推荐，让renew重新拉取）")
    logger.info("2. 删除daily不完整数据（daily必须重新拉取）")
    logger.info("3. 从日线修复weekly数据")
    logger.info("4. 从日线修复monthly数据")
    logger.info("5. 组合修复：删除daily + 修复weekly/monthly")
    logger.info("0. 退出")
    
    choice = input("\n请选择 (0-5): ").strip()
    
    if choice == '0':
        logger.info("退出")
        return
    
    elif choice == '1':
        # 删除所有不完整数据
        delete_incomplete_records(db, term=None)
    
    elif choice == '2':
        # 只删除daily不完整数据
        if 'daily' in incomplete_stats:
            delete_incomplete_records(db, term='daily')
        else:
            logger.info("✅ daily没有不完整数据")
    
    elif choice == '3':
        # 修复weekly
        if 'weekly' in incomplete_stats:
            fix_weekly_monthly_from_daily(db, term='weekly')
        else:
            logger.info("✅ weekly没有不完整数据")
    
    elif choice == '4':
        # 修复monthly
        if 'monthly' in incomplete_stats:
            fix_weekly_monthly_from_daily(db, term='monthly')
        else:
            logger.info("✅ monthly没有不完整数据")
    
    elif choice == '5':
        # 组合修复
        logger.info("\n📋 组合修复方案:")
        logger.info("  1. 删除daily不完整数据")
        logger.info("  2. 修复weekly数据")
        logger.info("  3. 修复monthly数据")
        
        confirm = input("\n确认执行？(yes/no): ")
        if confirm.lower() != 'yes':
            logger.info("❌ 取消操作")
            return
        
        # 1. 删除daily
        if 'daily' in incomplete_stats:
            logger.info("\n步骤1: 删除daily不完整数据")
            delete_incomplete_records(db, term='daily')
        
        # 2. 修复weekly
        if 'weekly' in incomplete_stats:
            logger.info("\n步骤2: 修复weekly数据")
            fix_weekly_monthly_from_daily(db, term='weekly')
        
        # 3. 修复monthly
        if 'monthly' in incomplete_stats:
            logger.info("\n步骤3: 修复monthly数据")
            fix_weekly_monthly_from_daily(db, term='monthly')
        
        logger.success("\n✅ 组合修复完成！")
    
    else:
        logger.error("❌ 无效选项")
    
    # 再次扫描
    logger.info("\n" + "=" * 60)
    logger.info("重新扫描...")
    logger.info("=" * 60)
    incomplete_stats, total_count = find_incomplete_records(db)
    
    if total_count == 0:
        logger.success("\n🎉 所有数据已修复！")
    else:
        logger.warning(f"\n⚠️  仍有 {total_count} 条不完整数据")
        logger.info("建议：")
        logger.info("  - daily数据：必须删除，让renew重新拉取")
        logger.info("  - weekly/monthly数据：可以继续修复或删除")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  操作被中断")
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
