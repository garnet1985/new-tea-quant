#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta
from utils.worker.futures_worker import FuturesWorker
from .historic_low_settings import invest_settings
from .tables.meta.model import HLMetaModel
from .tables.opportunity_history.model import HLOpportunityHistoryModel
from .tables.strategy_summary.model import HLStrategySummaryModel
from ..base_strategy import BaseStrategy


class HistoricLowStrategy(BaseStrategy):
    """HistoricLow 策略实现"""
    
    def __init__(self, db_manager):
        """
        初始化 HistoricLow 策略
        
        Args:
            db_manager: 已初始化的数据库管理器实例
        """
        super().__init__(
            db_manager,
            "Historic Low",
            "HL"
        )
        
        self.strategy_description = "寻找股票的历史低点，识别可能的买入机会"
        
        # 加载策略设置
        self.settings = invest_settings
        
        # 初始化策略所需的表模型
        self._initialize_tables()
    
    def _initialize_tables(self):
        """初始化策略所需的表模型"""
        self.required_tables = {
            "meta": HLMetaModel(self.db),
            "opportunity_history": HLOpportunityHistoryModel(self.db),
            "strategy_summary": HLStrategySummaryModel(self.db)
        }
        
        self.log_info("表模型初始化完成")
    
    def scan(self) -> List[Dict[str, Any]]:
        """
        扫描投资机会
        
        Returns:
            List[Dict]: 投资机会列表
        """
        self.log_info("开始扫描投资机会...")
        
        # 获取股票列表
        stock_idx = self._get_stock_index()
        if not stock_idx:
            self.log_warning("未找到可扫描的股票")
            return []
        
        self.log_info(f"找到 {len(stock_idx)} 只股票，开始扫描...")
        
        # 使用多线程扫描
        opportunities = self._scan_stocks_with_worker(stock_idx)
        
        # 保存扫描结果
        if opportunities:
            self._save_meta(opportunities)
        
        self.log_info(f"扫描完成，发现 {len(opportunities)} 个投资机会")
        return opportunities
    
    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描结果
        
        Args:
            opportunities: 投资机会列表
        """
        self._present_report(opportunities)
    
    def test(self) -> None:
        """测试策略 - 使用历史数据模拟"""
        self.log_info("开始策略测试...")
        
        # 这里可以实现历史数据回测逻辑
        # 暂时简单实现
        test_opportunities = [
            {
                'code': '000001.SZ',
                'name': '平安银行',
                'close': 10.50,
                'low_price': 8.20,
                'opportunity_range': '8.20-9.02',
                'loss': 7.38,
                'win': 12.60,
                'scan_terms': ['3M', '6M', '1Y', 'ALL'],
                'date': datetime.now().strftime('%Y%m%d')
            }
        ]
        
        self.report(test_opportunities)
        self.log_info("策略测试完成")
    
    def _get_stock_index(self) -> List[Dict[str, Any]]:
        """获取股票列表，排除科创板等"""
        try:
            sql = """
                SELECT code, name, market 
                FROM stock_index 
                WHERE code NOT LIKE %s 
                AND code NOT LIKE %s 
                AND code NOT LIKE %s
                ORDER BY code
            """
            params = ('688%', '%BJ%', '%BJ')
            
            result = self.db.execute_sync_query(sql, params)
            return result
            
        except Exception as e:
            self.log_error(f"获取股票列表失败: {e}")
            return []
    
    def _scan_stocks_with_worker(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用多线程扫描股票"""
        opportunities = []
        
        # 创建任务
        jobs = []
        for stock in stock_idx:
            job_id = f"scan_{stock['code']}"
            jobs.append({
                'id': job_id,
                'data': stock
            })
        
        # 使用 FuturesWorker 并行处理
        worker = FuturesWorker(
            max_workers=10,
            enable_monitoring=True
        )
        
        # 设置任务执行函数
        worker.set_job_executor(self.scan_job)
        
        # 添加任务
        for job in jobs:
            worker.add_job(job['id'], job['data'])
        
        # 执行任务
        worker.run_jobs()
        
        # 获取结果
        results = worker.get_results()
        
        # 收集结果
        for result in results:
            if result.status.value == 'completed' and result.result:
                opportunities.extend(result.result)
        
        return opportunities
    
    def scan_job(self, stock: Dict[str, Any]) -> List[Dict[str, Any]]:
        """扫描单个股票"""
        try:
            # 准备数据
            daily_data, monthly_data = self._prepare_data(stock)
            if not daily_data or not monthly_data:
                return []
            
            # 获取最新日线记录
            latest_daily_record = daily_data[0] if daily_data else None
            if not latest_daily_record:
                return []
            
            # 寻找投资机会
            opportunities = self._find_opportunity(stock, latest_daily_record, monthly_data)
            
            return opportunities
            
        except Exception as e:
            self.log_error(f"扫描股票 {stock['code']} 失败: {e}")
            return []
    
    def _prepare_data(self, stock: Dict[str, Any]) -> tuple:
        """准备股票数据"""
        try:
            # 获取日线数据
            daily_sql = """
                SELECT date, close, lowest, highest, open, volume, amount
                FROM stock_kline 
                WHERE code = %s AND term = 'daily'
                ORDER BY date DESC 
                LIMIT 100
            """
            daily_data = self.db.execute_sync_query(daily_sql, (stock['code'],))
            
            # 获取月线数据
            monthly_sql = """
                SELECT date, close, lowest, highest, open, volume, amount
                FROM stock_kline 
                WHERE code = %s AND term = 'monthly'
                ORDER BY date DESC 
                LIMIT 60
            """
            monthly_data = self.db.execute_sync_query(monthly_sql, (stock['code'],))
            
            # 检查数据是否足够
            if len(monthly_data) < 12:  # 至少需要12个月的数据
                return [], []
            
            return daily_data, monthly_data
            
        except Exception as e:
            self.log_error(f"准备股票 {stock['code']} 数据失败: {e}")
            return [], []
    
    def _find_opportunity(self, stock: Dict[str, Any], latest_daily_record: Dict[str, Any], monthly_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """寻找投资机会"""
        try:
            # 寻找最低点记录
            low_points = self._find_lowest_records(stock, monthly_data)
            if not low_points:
                return []
            
            # 从最低点寻找机会
            opportunities = self._find_opportunity_from_low_points(stock, low_points, latest_daily_record)
            
            return opportunities
            
        except Exception as e:
            self.log_error(f"寻找股票 {stock['code']} 机会失败: {e}")
            return []
    
    def _find_lowest_records(self, stock: Dict[str, Any], monthly_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """寻找最低点记录"""
        low_points = []
        
        # 为每个扫描周期寻找最低点
        for term in self.settings['scan_terms']:
            if term == 'ALL':
                # 所有历史数据
                records = monthly_records
            else:
                # 根据周期筛选数据 - term 已经是整数（月份数）
                months = term
                
                if len(monthly_records) >= months:
                    records = monthly_records[:months]
                else:
                    continue
            
            # 寻找最低点
            lowest_record = self._find_lowest_record(records)
            if lowest_record:
                low_points.append({
                    'term': term,
                    'record': lowest_record
                })
        
        return low_points
    
    def _find_lowest_record(self, records: List[Dict[str, Any]], amount: float = None) -> Dict[str, Any]:
        """在记录中寻找最低点"""
        if not records:
            return None
        
        lowest_record = min(records, key=lambda x: x['lowest'])
        
        # 如果指定了金额，检查是否满足条件
        if amount is not None:
            if lowest_record['lowest'] > amount:
                return None
        
        return lowest_record
    
    def _find_opportunity_from_low_points(self, stock: Dict[str, Any], low_points: List[Dict[str, Any]], latest_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从最低点寻找投资机会"""
        opportunities = []
        
        for low_point in low_points:
            # 检查当前价格是否在投资范围内
            if self._is_in_invest_range(latest_record, low_point):
                opportunity = {
                    'code': stock['code'],
                    'name': stock['name'],
                    'close': float(latest_record['close']),
                    'low_price': float(low_point['record']['lowest']),
                    'opportunity_range': f"{float(low_point['record']['lowest']):.2f}-{float(low_point['record']['lowest']) * 1.1:.2f}",
                    'loss': self._set_loss(latest_record),
                    'win': self._set_win(latest_record),
                    'scan_terms': [low_point['term']],
                    'date': latest_record['date']
                }
                opportunities.append(opportunity)
        
        return opportunities
    
    def _is_in_invest_range(self, record: Dict[str, Any], low_point: Dict[str, Any]) -> bool:
        """检查是否在投资范围内"""
        low_price = float(low_point['record']['lowest'])
        current_price = float(record['close'])
        
        # 计算投资范围
        range_high = low_price * (1 + self.settings['goal']['opportunityRange'])
        
        return low_price <= current_price <= range_high
    
    def _set_loss(self, record: Dict[str, Any]) -> float:
        """设置止损价格"""
        return float(record['close']) * (1 - self.settings['goal']['loss'])
    
    def _set_win(self, record: Dict[str, Any]) -> float:
        """设置止盈价格"""
        return float(record['close']) * (1 + self.settings['goal']['win'])
    
    def _present_report(self, opportunities: List[Dict[str, Any]]) -> None:
        """呈现扫描报告"""
        if not opportunities:
            print("\n📊 HistoricLow 策略扫描报告")
            print("=" * 50)
            print("❌ 未发现投资机会")
            return
        
        print("\n📊 HistoricLow 策略扫描报告")
        print("=" * 50)
        print(f"🎯 发现 {len(opportunities)} 个投资机会")
        print("=" * 50)
        
        for i, opp in enumerate(opportunities, 1):
            print(f"\n{i}. {opp['code']} - {opp['name']}")
            print(f"   当前价格: {opp['close']:.2f}")
            print(f"   历史低点: {opp['low_price']:.2f}")
            print(f"   投资范围: {opp['opportunity_range']}")
            print(f"   止损价格: {opp['loss']:.2f}")
            print(f"   止盈价格: {opp['win']:.2f}")
            print(f"   扫描周期: {', '.join(opp['scan_terms'])}")
            print(f"   扫描日期: {opp['date']}")
    
    def _save_meta(self, opportunities: List[Dict[str, Any]]) -> None:
        """保存扫描结果到元数据表"""
        try:
            # 准备元数据
            meta_data = {
                'date': datetime.now().strftime('%Y%m%d'),
                'lastOpportunityUpdateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'lastSuggestedStockCodes': [opp['code'] for opp in opportunities]
            }
            
            # 使用元数据表模型保存
            meta_table = self.required_tables['meta']
            meta_table.update_meta(
                date=meta_data['date'],
                last_opportunity_update_time=meta_data['lastOpportunityUpdateTime'],
                last_suggested_stock_codes=','.join(meta_data['lastSuggestedStockCodes'])
            )
            
            self.log_info("扫描结果已保存到元数据表")
            
        except Exception as e:
            self.log_error(f"保存扫描结果失败: {e}")
    
    def _to_digit(self, num: float, digit: int = 2) -> float:
        """格式化数字"""
        return round(num, digit)





    # def test(self):
    #     return super().test()

    
