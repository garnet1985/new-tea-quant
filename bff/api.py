"""
BFF API 业务逻辑
"""

import sys
import os
from flask import jsonify
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
from app.analyzer.strategy.historicLow.strategy_simulator import HLSimulator
from app.analyzer.analyzer_service import AnalyzerService
from app.data_source.data_source_service import DataSourceService
from utils.db.db_manager import DatabaseManager
from utils.db.tables.stock_kline.model import StockKlineModel
from utils.db.tables.adj_factor.model import AdjustFactor

class BFFApi:
    def __init__(self):
        """初始化BFF API"""
        self.db = DatabaseManager()
        self.analyzer_service = AnalyzerService()
        
        # 延迟初始化策略相关，避免自动创建tmp目录
        self.strategy = None
        self.simulator = None
        # 分离HL相关组件的初始化
        self._hl_components_initialized = False


        self.tables = {
            "stock_kline": self.db.get_table_instance("stock_kline"),
            "adj_factor": self.db.get_table_instance("adj_factor"),
            "stock_index": self.db.get_table_instance("stock_index")
        }
        


    def _init_hl_components_if_needed(self):
        """延迟初始化HL相关组件，只在需要时才创建"""
        if not self._hl_components_initialized:
            from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
            from app.analyzer.strategy.historicLow.strategy_simulator import HLSimulator
            
            self.strategy = HistoricLowStrategy(self.db)
            # 注意：这里不会自动创建InvestmentRecorder，因为HLSimulator的__init__被注释了
            self.simulator = HLSimulator(self.strategy)
            self._hl_components_initialized = True
    

    def health_check(self):
        """健康检查"""
        return jsonify({
            "success": True,
            "message": "BFF API 运行正常",
            "timestamp": "当前时间"
        })

    def get_stock_kline(self, stock_id: str, term: str = 'daily'):
        """
        获取股票K线数据
        
        Args:
            stock_id: 股票ID (如: 000002.SZ)
            term: K线周期 (daily, monthly)
            
        Returns:
            dict: 包含K线数据的响应
        """
        try:
            stock_kline_model = self.tables["stock_kline"]
            adj_factor_model = self.tables["adj_factor"]

            # 获取原始K线数据
            klines = stock_kline_model.get_all_k_lines_by_term(stock_id, term)

            if not klines:
                return jsonify({
                    "success": False,
                    "message": f"未找到股票 {stock_id} 的 {term} K线数据",
                    "data": None
                }), 404

            # 获取复权因子
            qfq_factors = adj_factor_model.get_stock_factors(stock_id)

            # 处理复权因子：对于没有复权因子的时间段，使用第一个复权因子
            if qfq_factors:
                # 按日期排序
                sorted_factors = sorted(qfq_factors, key=lambda x: x['date'])
                first_factor = sorted_factors[0]
                
                # 为每条K线添加默认复权因子（如果没有找到对应的因子）
                for kline in klines:
                    current_date = kline.get('date')
                    if not current_date:
                        continue
                    
                    # 查找对应的复权因子
                    qfq_factor = DataSourceService._find_qfq_factor(current_date, sorted_factors)
                    
                    # 如果没有找到复权因子，使用第一个（最早的）复权因子
                    if qfq_factor is None:
                        qfq_factor = first_factor['qfq']
                    
                    # 将复权因子添加到K线数据中，供to_qfq方法使用
                    kline['qfq_factor'] = qfq_factor

            # 使用DataSource类的to_qfq方法复权
            qfq_klines = DataSourceService.to_qfq(klines, qfq_factors)
            
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": {
                    "stock_id": stock_id,
                    "term": term,
                    "total_records": len(qfq_klines),
                    "klines": qfq_klines
                }
            })
            
        except Exception as e:
            logger.error(f"获取股票K线失败: {e}")
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}",
                "data": None
            }), 500

    def get_stock_simulate(self, strategy: str, stock_id: str):
        """
        获取股票策略模拟结果
        
        Args:
            strategy: 策略名称 (如: historicLow)
            term: K线周期 (daily, monthly)
            
        Returns:
            dict: 包含模拟结果的响应
        """
        try:
            if strategy.lower() != 'historiclow':
                return jsonify({
                    "success": False,
                    "message": f"暂不支持策略: {strategy}",
                    "data": None
                }), 400
            
            # 获取股票基本信息
            stock_info = {
                'id': stock_id,
                'name': 'Unknown',  # 可以从数据库获取
                'market': stock_id.split('.')[-1] if '.' in stock_id else ''
            }
            
            # 运行模拟
            # 注意：这里需要根据实际情况调整模拟逻辑
            # 可能需要先准备数据，然后运行模拟
            
            return jsonify({
                "success": True,
                "message": "模拟完成",
                "data": {
                    "strategy": strategy,
                    "stock_id": stock_id,
                    "simulation_result": "模拟结果待实现"
                }
            })
            
        except Exception as e:
            logger.error(f"股票模拟失败: {e}")
            return jsonify({
                "success": False,
                "message": f"模拟失败: {str(e)}",
                "data": None
            }), 500

    def get_stock_scan(self, strategy: str, stock_id: str):
        """
        获取股票策略扫描结果
        
        Args:
            strategy: 策略名称 (如: historicLow)
            stock_id: 股票ID (如: 000002.SZ)
            
        Returns:
            dict: 包含扫描结果的响应
        """
        try:
            if strategy.lower() != 'historiclow':
                return jsonify({
                    "success": False,
                    "message": f"暂不支持策略: {strategy}",
                    "data": None
                }), 400
            
            # 获取股票基本信息
            stock_info = {
                'id': stock_id,
                'name': 'Unknown',  # 可以从数据库获取
                'market': stock_id.split('.')[-1] if '.' in stock_id else ''
            }
            
            # 运行策略扫描
            opportunities = self.strategy.scan_job(stock_info)
            
            return jsonify({
                "success": True,
                "message": "扫描完成",
                "data": {
                    "strategy": strategy,
                    "stock_id": stock_id,
                    "scan_time": "当前时间",
                    "opportunities": opportunities,
                    "total_opportunities": len(opportunities)
                }
            })
            
        except Exception as e:
            logger.error(f"股票扫描失败: {e}")
            return jsonify({
                "success": False,
                "message": f"扫描失败: {str(e)}",
                "data": None
            }), 500

    def get_stock_hl_analysis(self, stock_id: str):
        """
        获取股票的HL策略分析结果
        
        Args:
            stock_id: 股票ID (如: 000002.SZ)
            
        Returns:
            dict: 包含HL分析结果的响应
        """
        try:
            # 延迟初始化HL相关组件（如果需要）
            self._init_hl_components_if_needed()
            
            # 获取HL模拟结果和投资点位
            hl_data = self._get_hl_analysis_data(stock_id)
            
            return jsonify({
                "success": True,
                "message": "获取成功",
                "data": hl_data
            })
            
        except Exception as e:
            logger.error(f"获取HL分析失败: {e}")
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}",
                "data": None
            }), 500

    def _get_hl_analysis_data(self, stock_id: str) -> dict:
        """
        获取HL策略分析数据
        
        Args:
            stock_id: 股票ID
            
        Returns:
            dict: HL分析数据
        """
        import os
        import json
        from datetime import datetime
        
        # 获取HL tmp目录路径
        hl_tmp_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'app', 'analyzer', 'strategy', 'historicLow', 'tmp'
        )
        
        if not os.path.exists(hl_tmp_path):
            # 返回空数据，表示没有运行过策略
            return {
                "session_id": None,
                "stock_id": stock_id,
                "data": None
            }
        
        # 找到最新的模拟会话
        sessions = []
        for item in os.listdir(hl_tmp_path):
            item_path = os.path.join(hl_tmp_path, item)
            if os.path.isdir(item_path) and '-' in item:
                sessions.append(item)
        
        if not sessions:
            # 返回空数据，表示没有运行过策略
            return {
                "session_id": None,
                "stock_id": stock_id,
                "data": None
            }
        
        # 按日期排序，获取最新会话
        sessions.sort(reverse=True)
        latest_session = sessions[0]
        session_path = os.path.join(hl_tmp_path, latest_session)
        
        # 直接查找股票ID对应的JSON文件
        stock_file_path = os.path.join(session_path, f"{stock_id}.json")
        
        if not os.path.exists(stock_file_path):
            # 返回空数据，表示该股票没有投资记录
            return {
                "session_id": latest_session,
                "stock_id": stock_id,
                "data": None
            }
        
        try:
            # 读取股票投资记录文件
            with open(stock_file_path, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
            
            # 直接返回原始数据，让前端处理分类
            return {
                "session_id": latest_session,
                "stock_id": stock_id,
                "data": stock_data  # 返回完整的原始数据
            }
            
        except Exception as e:
            logger.error(f"读取股票投资记录失败 {stock_file_path}: {e}")
            return {
                "session_id": latest_session,
                "stock_id": stock_id,
                "data": None
            }
