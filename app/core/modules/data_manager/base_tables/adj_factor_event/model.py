"""
复权因子事件 Model

只存储复权因子变化的日期（除权除息日），不存储每日因子。
用于优化存储和计算前复权价格。
"""
from typing import List, Dict, Any, Optional
from loguru import logger
import pandas as pd
import os
from datetime import datetime
from pathlib import Path
from app.core.infra.db import DbBaseModel
from app.core.utils.date.date_utils import DateUtils


class AdjFactorEventModel(DbBaseModel):
    """复权因子事件 Model"""
    
    def __init__(self, db=None):
        super().__init__('adj_factor_event', db)
        # CSV 文件目录：放在项目根下的 app/core/modules/data_manager/base_tables/adj_factor_event
        # 为了避免硬编码层级，这里通过查找项目中的 app 目录来推断项目根
        current_path = Path(__file__).resolve()  # .../app/core/modules/data_manager/base_tables/adj_factor_event/model.py
        project_root: Path = None
        for parent in current_path.parents:
            if parent.name == "app":
                # app 的上一级目录视为项目根
                project_root = parent.parent
                break
        if project_root is None:
            # 兜底：如果未找到 app 目录，退回到 5 级以上父目录作为项目根
            project_root = current_path.parents[5]
        self.csv_dir = str(
            project_root / "app" / "core" / "modules" / "data_manager" / "base_tables" / "adj_factor_event"
        )
        os.makedirs(self.csv_dir, exist_ok=True)
    
    def is_table_empty(self) -> bool:
        """
        判断表是否为空
        
        Returns:
            bool: 如果表为空返回 True，否则返回 False
        """
        return self.count() == 0
    
    def load_stocks_need_update(self, days: int = 15) -> List[str]:
        """
        查询超过N天未更新的股票列表
        
        通过查询每个股票的最新 event_date，找出距离现在超过N天的股票。
        
        Args:
            days: 更新阈值天数（默认15天）
        
        Returns:
            List[str]: 需要更新的股票代码列表
        """
        # 使用 SQL 查询：找出每个股票的最新 event_date，然后筛选超过N天的
        # event_date 是 YYYYMMDD 格式的字符串，需要转换为日期进行比较
        query = f"""
            SELECT id, MAX(event_date) as latest_event_date
            FROM {self.table_name}
            GROUP BY id
            HAVING STR_TO_DATE(latest_event_date, '%%Y%%m%%d') < DATE_SUB(CURDATE(), INTERVAL %s DAY)
            OR latest_event_date IS NULL
        """
        
        try:
            results = self.db.execute_sync_query(query, (days,))
            stock_ids = [row['id'] for row in results]
            logger.debug(f"查询到 {len(stock_ids)} 只股票超过 {days} 天未更新")
            return stock_ids
        except Exception as e:
            logger.error(f"查询需要更新的股票失败: {e}")
            return []
    
    def get_current_quarter_csv_name(self, base_date: Optional[str] = None) -> str:
        """
        获取当前表数据对应季度的 CSV 文件名
        
        格式：adj_factor_events_YYYYQn.csv
        例如：adj_factor_events_2024Q4.csv
        
        命名规则：
        - 优先根据传入的 base_date（通常是 latest_completed_trading_date）计算“上一个完整季度”
        - 如果未提供 base_date，则根据当前日期计算“上一个完整季度”
        
        Returns:
            str: CSV文件名
        """
        # 情况 1：提供了 base_date（YYYYMMDD 或 YYYY-MM-DD）
        if base_date:
            try:
                date_str = str(base_date).replace("-", "")
                target_date = datetime.strptime(date_str[:8], "%Y%m%d")
            except Exception as e:
                logger.warning(f"根据 base_date 解析季度失败，将退回使用当前日期: {e}")
                target_date = datetime.now()
        else:
            # 情况 2：未提供 base_date，使用当前日期
            target_date = datetime.now()
        
        # 先求出 target_date 所在季度
        year = target_date.year
        quarter = (target_date.month - 1) // 3 + 1
        
        # 我们要的是“已经完成的上一个季度”
        if quarter > 1:
            quarter -= 1
        else:
            quarter = 4
            year -= 1
        
        return f"adj_factor_events_{year}Q{quarter}.csv"
    
    def get_latest_csv_file(self) -> Optional[str]:
        """
        获取最新的CSV文件路径
        
        查找目录下所有符合命名格式的CSV文件，返回最新的一个。
        
        Returns:
            Optional[str]: 最新CSV文件的完整路径，如果不存在返回 None
        """
        import glob
        
        # 匹配格式：adj_factor_events_YYYYQn.csv
        pattern = os.path.join(self.csv_dir, "adj_factor_events_*Q*.csv")
        csv_files = glob.glob(pattern)
        
        if not csv_files:
            return None
        
        # 按文件名排序（文件名包含季度信息，可以直接排序）
        csv_files.sort(reverse=True)
        return csv_files[0]
    
    def import_from_csv(self, file_path: str = None) -> int:
        """
        从CSV文件导入数据
        
        CSV格式：id,event_date,factor,qfq_diff
        
        Args:
            file_path: CSV文件路径（如果为None，自动查找最新的CSV文件）
        
        Returns:
            int: 导入的记录数
        """
        if file_path is None:
            file_path = self.get_latest_csv_file()
            if file_path is None:
                logger.warning("未找到CSV文件，无法导入")
                return 0
        
        if not os.path.exists(file_path):
            logger.warning(f"CSV文件不存在: {file_path}")
            return 0
        
        try:
            # 读取CSV
            df = pd.read_csv(file_path)
            
            # 检查必需的列（包括 qfq_diff，保持与导出格式一致）
            required_columns = ['id', 'event_date', 'factor', 'qfq_diff']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"CSV文件缺少必需的列: {missing_columns}")
                return 0
            
            # 转换数据格式
            events = []
            for _, row in df.iterrows():
                event_date_str = str(row['event_date'])
                # 统一转换为 YYYYMMDD 格式
                if '-' in event_date_str:
                    event_date_ymd = event_date_str.replace('-', '')
                else:
                    event_date_ymd = event_date_str
                
                event = {
                    'id': str(row['id']),
                    'event_date': event_date_ymd,  # YYYYMMDD 格式
                    'factor': float(row['factor']),
                    'qfq_diff': float(row.get('qfq_diff', 0.0)),
                }
                events.append(event)
            
            # 批量保存
            saved_count = self.save_events(events)
            logger.info(f"✅ 从CSV导入 {saved_count} 条复权因子事件记录: {file_path}")
            return saved_count
            
        except Exception as e:
            logger.error(f"导入CSV文件失败: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def export_to_csv(self, file_path: str = None) -> int:
        """
        导出数据到CSV文件
        
        CSV格式：id,event_date,factor,qfq_diff
        
        Args:
            file_path: CSV文件路径（如果为None，使用当前季度的文件名）
        
        Returns:
            int: 导出的记录数
        """
        if file_path is None:
            file_name = self.get_current_quarter_csv_name()
            file_path = os.path.join(self.csv_dir, file_name)
        
        try:
            # 查询所有数据
            all_events = self.load_all()
            
            if not all_events:
                logger.warning("表为空，无法导出CSV")
                return 0
            
            # 为了节约存储空间，始终只保留一份 CSV：
            # 删除目录下已有的季度 CSV 文件，再生成新的快照
            try:
                import glob
                pattern = os.path.join(self.csv_dir, "adj_factor_events_*Q*.csv")
                for existing in glob.glob(pattern):
                    if os.path.abspath(existing) != os.path.abspath(file_path):
                        try:
                            os.remove(existing)
                        except Exception as e:
                            logger.warning(f"删除旧的季度CSV失败: {existing}, 错误: {e}")
            except Exception as e:
                logger.warning(f"清理旧的季度CSV时出错，将继续导出新文件: {e}")
            
            # 转换为DataFrame
            df = pd.DataFrame(all_events)
            
            # 只保留需要的列
            export_columns = ['id', 'event_date', 'factor', 'qfq_diff']
            df_export = df[export_columns].copy()
            
            # 保存为CSV
            df_export.to_csv(file_path, index=False, encoding='utf-8')
            
            logger.info(f"✅ 导出 {len(df_export)} 条复权因子事件记录到CSV: {file_path}")
            return len(df_export)
            
        except Exception as e:
            logger.error(f"导出CSV文件失败: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """
        查询指定股票的所有复权因子事件
        
        Args:
            stock_id: 股票代码
        
        Returns:
            复权因子事件列表，按日期升序排列
        """
        return self.load("id = %s", (stock_id,), order_by="event_date ASC")
    
    def load_all_stock_ids(self) -> List[str]:
        """
        查询当前表中已经存在复权因子事件的股票ID列表（去重）。
        
        Returns:
            List[str]: 已有复权因子事件记录的股票ID列表
        """
        try:
            sql = f"SELECT DISTINCT id FROM {self.table_name}"
            rows = self.db.execute_sync_query(sql)
            return [row['id'] for row in rows]
        except Exception as e:
            logger.error(f"查询已有复权因子股票ID失败: {e}")
            return []
    
    def load_by_date_range(
        self, 
        stock_id: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        查询指定日期范围的复权因子事件
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（YYYY-MM-DD 或 YYYYMMDD）
            end_date: 结束日期（YYYY-MM-DD 或 YYYYMMDD）
        
        Returns:
            复权因子事件列表
        """
        return self.load(
            "id = %s AND event_date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="event_date ASC"
        )
    
    def load_factors_by_range(
        self,
        stock_id: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        查询指定日期范围内的所有复权因子事件（用于K线复权计算）
        
        返回该日期范围内的所有复权因子和 qfq_diff，按日期升序排列。
        如果 end_date 为 None，返回从 start_date 到最新的所有记录。
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（可选，YYYYMMDD），如果为 None 则查询到最新
        
        Returns:
            复权因子事件列表，每个事件包含：
                - id: 股票代码
                - event_date: 除权日期（YYYYMMDD）
                - factor: 复权因子
                - qfq_diff: 价格差异
        """
        # 确保日期格式为 YYYYMMDD
        start_date_ymd = start_date.replace('-', '') if '-' in start_date else start_date
        if end_date:
            end_date_ymd = end_date.replace('-', '') if '-' in end_date else end_date
            query = "id = %s AND event_date >= %s AND event_date <= %s"
            return self.load(query, (stock_id, start_date_ymd, end_date_ymd), order_by="event_date ASC")
        else:
            query = "id = %s AND event_date >= %s"
            return self.load(query, (stock_id, start_date_ymd), order_by="event_date ASC")
    
    def load_factor_by_date(self, stock_id: str, date: str) -> Optional[Dict[str, Any]]:
        """
        查询指定日期的复权因子（使用最近的有效因子）
        
        如果指定日期没有复权事件，返回该日期之前最近的一个复权因子事件。
        
        Args:
            stock_id: 股票代码
            date: 查询日期（YYYYMMDD）
        
        Returns:
            复权因子事件字典，包含 factor 和 qfq_diff
        """
        # 确保日期格式为 YYYYMMDD
        date_ymd = date.replace('-', '') if '-' in date else date
        return self.load_one(
            "id = %s AND event_date <= %s",
            (stock_id, date_ymd),
            order_by="event_date DESC"
        )
    
    def load_latest_factor(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        查询股票的最新复权因子
        
        Args:
            stock_id: 股票代码
        
        Returns:
            最新的复权因子事件字典
        """
        return self.load_one(
            "id = %s",
            (stock_id,),
            order_by="event_date DESC"
        )
    
    def load_latest_factors_batch(self, stock_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量查询多只股票的最新复权因子
        
        Args:
            stock_ids: 股票代码列表
        
        Returns:
            Dict[str, Optional[Dict]]: {stock_id: 最新复权因子事件字典}，如果没有数据则为 None
        """
        if not stock_ids:
            return {}
        
        # 使用 SQL 查询：为每只股票获取最新的 event_date 记录
        # 使用窗口函数 ROW_NUMBER() 来获取每只股票的最新记录
        placeholders = ','.join(['%s'] * len(stock_ids))
        query = f"""
            SELECT t1.*
            FROM (
                SELECT 
                    id,
                    event_date,
                    factor,
                    qfq_diff,
                    last_update,
                    ROW_NUMBER() OVER (PARTITION BY id ORDER BY event_date DESC) as rn
                FROM {self.table_name}
                WHERE id IN ({placeholders})
            ) t1
            WHERE t1.rn = 1
        """
        
        try:
            results = self.db.execute_sync_query(query, tuple(stock_ids))
            
            # 构建结果字典
            result_map = {stock_id: None for stock_id in stock_ids}
            for row in results:
                stock_id = row['id']
                # 移除 rn 字段
                row_dict = {k: v for k, v in row.items() if k != 'rn'}
                result_map[stock_id] = row_dict
            
            return result_map
        except Exception as e:
            logger.error(f"批量查询最新复权因子失败: {e}")
            # 降级为单次查询
            result_map = {}
            for stock_id in stock_ids:
                result_map[stock_id] = self.load_latest_factor(stock_id)
            return result_map
    
    def load_latest_qfq_diff(self, stock_id: str, date: str) -> float:
        """
        查询与EastMoney前复权价格的价格差异（使用最近的有效差异）
        
        Args:
            stock_id: 股票代码
            date: 查询日期（YYYYMMDD）
        
        Returns:
            qfq_diff，如果没有找到返回 0.0
        """
        result = self.load_factor_by_date(stock_id, date)
        if result and result.get('qfq_diff') is not None:
            return float(result['qfq_diff'])
        return 0.0
    
    def save_event(
        self, 
        stock_id: str, 
        event_date: str, 
        factor: float, 
        qfq_diff: float = 0.0
    ) -> int:
        """
        保存复权因子事件（自动去重）
        
        Args:
            stock_id: 股票代码
            event_date: 除权日期（YYYYMMDD）
            factor: 复权因子
            qfq_diff: 与EastMoney前复权价格的价格差异
        
        Returns:
            影响的行数
        """
        # 确保日期格式为 YYYYMMDD
        event_date_ymd = event_date.replace('-', '') if '-' in event_date else event_date
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        event_data = {
            'id': stock_id,
            'event_date': event_date_ymd,
            'factor': factor,
            'qfq_diff': qfq_diff,
            'last_update': now,
        }
        
        return self.replace([event_data], unique_keys=['id', 'event_date'])
    
    def save_events(self, events: List[Dict[str, Any]]) -> int:
        """
        批量保存复权因子事件（自动去重）
        
        Args:
            events: 复权因子事件列表，每个事件必须包含：
                - id: 股票代码
                - event_date: 除权日期（YYYYMMDD）
                - factor: 复权因子
                - qfq_diff: 价格差异（可选，默认0.0）
        
        Returns:
            影响的行数
        """
        if not events:
            return 0
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        normalized_events: List[Dict[str, Any]] = []
        for e in events:
            data = dict(e)
            # 确保 event_date 为 YYYYMMDD 格式
            if 'event_date' in data:
                event_date_str = str(data['event_date'])
                data['event_date'] = event_date_str.replace('-', '') if '-' in event_date_str else event_date_str
            data.setdefault('last_update', now)
            normalized_events.append(data)
        
        return self.replace(normalized_events, unique_keys=['id', 'event_date'])
