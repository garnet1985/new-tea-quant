#!/usr/bin/env python3
"""
历史低点策略
寻找股票的历史低点，识别可能的买入机会
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger

# 导入抽象基类
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from base_strategy import BaseStrategy

# 导入服务类
from .service import HistoricLowService
from .simulator import HistoricLowSimulator


class HistoricLowStrategy(BaseStrategy):
    """历史低点策略"""
    
    def __init__(self):
        super().__init__()
        
        # 策略基本信息
        self.strategy_name = "Historic Low (HL)"
        self.strategy_description = "寻找股票的历史低点，识别可能的买入机会"
        self.prefix = "HL"
        self.is_enabled = True
        
        # 检查参数
        self.check_params()
        
        # 策略参数
        self.terms = [60, 96]  # 回看月数：5年和8年
        self.min_required_monthly_records = min(self.terms)
        self.low_points = []
        
        # 投资目标设置
        self.goal = {
            'loss': 0.8,  # 止损比例：可以承受20%损失
            'win': 1.5,   # 止盈比例：期望80%收益
            'opportunity_range': 0.05,  # 机会范围：历史低点5%范围内
            'kelly_criterion_divider': 5  # 凯利公式除数：投资态度谨慎程度
        }
        
        # 投资设置
        self.invest = {
            'meta': {
                'init_pool': 100000,  # 初始资金
                'start_date': "",
                'end_date': "",
                'min_purchase_size': 100,
                'invest_size_when_no_data': 1
            },
            'tracking': {
                'is_ended': False,
                'remaining_funds': 0,
                'investing': [],
                'completed': []
            },
            'summary': {
                'funds_when_end': 0,
                'funds_still_investing': 0,
                'total_wealth': 0,
                'profit': 0,
                'duration_in_days': 0
            }
        }
        
        # 计数器
        self.counter = 0
        self.all = 0
        
        # 服务类实例
        self.service = HistoricLowService()
    
    def test(self):
        """测试策略"""
        logger.info(f"测试策略: {self.strategy_name}")
        logger.info(f"策略描述: {self.strategy_description}")
        logger.info(f"回看月数: {self.terms}")
        logger.info(f"最小必需月线记录数: {self.min_required_monthly_records}")
        logger.info(f"投资目标: {self.goal}")
        return True
    
    def scan(self):
        """扫描机会"""
        logger.info(f"开始扫描 {self.strategy_name} 策略机会")
        
        try:
            # 获取股票指数
            stock_index = self._get_stock_index()
            if not stock_index:
                logger.warning("无法获取股票指数数据")
                return []
            
            # 获取策略元数据
            strategy_meta = self._get_strategy_meta()
            meta_of_today = strategy_meta[0] if strategy_meta else None
            
            # 分析元数据
            has_cache, should_simulate = self.service.analyze_meta(meta_of_today)
            
            # 如果需要模拟
            if should_simulate:
                logger.info("需要运行模拟")
                simulator = HistoricLowSimulator(self)
                simulator.run(stock_index, strategy_meta)
            
            # 如果有缓存
            if has_cache:
                logger.info("使用缓存数据")
                return self.service.parse_cache(strategy_meta)
            else:
                logger.info("扫描股票获取新机会")
                suggestions = self._scan_stocks(stock_index)
                self._set_meta(suggestions)
                return suggestions
                
        except Exception as e:
            logger.error(f"扫描策略时出错: {e}")
            return []
    
    def present(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """展示数据"""
        opportunities = data.get('opportunities', [])
        
        if not opportunities:
            logger.info("没有发现投资机会")
            return {"message": "没有发现投资机会"}
        
        logger.info(f"发现 {len(opportunities)} 个投资机会")
        
        # 链接模拟结果
        for opportunity in opportunities:
            self._link_to_simulation_result(opportunity)
        
        # 生成报告
        report = self._generate_report(opportunities)
        
        return {
            "strategy_name": self.strategy_name,
            "opportunities_count": len(opportunities),
            "report": report,
            "opportunities": opportunities
        }
    
    def _get_stock_index(self) -> List[Dict[str, Any]]:
        """获取股票指数"""
        # TODO: 从数据库获取股票指数
        # 这里需要集成数据库访问
        return []
    
    def _get_strategy_meta(self) -> List[Dict[str, Any]]:
        """获取策略元数据"""
        # TODO: 从数据库获取策略元数据
        return []
    
    def _scan_stocks(self, stock_index: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """扫描股票"""
        results = []
        
        for stock in stock_index:
            try:
                # 准备数据
                prepared_data = self._prepare_data(stock)
                if not prepared_data.get('should_count', False):
                    continue
                
                # 寻找机会
                opportunity = self._find_opportunity(
                    prepared_data['stock'],
                    prepared_data['latest_daily_record'],
                    prepared_data['monthly_k_lines']
                )
                
                if opportunity.get('is_opportunity', False):
                    results.append({
                        'stock': stock,
                        'result': opportunity
                    })
                    
            except Exception as e:
                logger.error(f"扫描股票 {stock.get('code', 'unknown')} 时出错: {e}")
                continue
        
        return results
    
    def _prepare_data(self, stock: Dict[str, Any]) -> Dict[str, Any]:
        """准备股票数据"""
        try:
            # TODO: 从数据库获取日线和月线数据
            # daily_lines = self._get_daily_k_lines(stock['code'], stock['market'])
            # monthly_lines = self._get_monthly_k_lines(stock['code'], stock['market'])
            
            # 模拟数据
            daily_lines = [{'date': '20250728', 'close': 10.5, 'lowest': 10.2}]
            monthly_lines = [{'date': '20250701', 'lowest': 9.8}] * 100
            
            if not daily_lines:
                return {
                    'should_count': False,
                    'reason': 'no stock records'
                }
            
            if len(monthly_lines) < self.min_required_monthly_records:
                return {
                    'should_count': False,
                    'reason': 'not enough records'
                }
            
            return {
                'should_count': True,
                'stock': stock,
                'latest_daily_record': daily_lines[0],
                'monthly_k_lines': monthly_lines
            }
            
        except Exception as e:
            logger.error(f"准备股票数据时出错: {e}")
            return {'should_count': False, 'reason': str(e)}
    
    def _find_opportunity(self, stock: Dict[str, Any], latest_daily_record: Dict[str, Any], monthly_k_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """寻找投资机会"""
        low_points = self._find_lowest_records(stock, monthly_k_lines)
        return self._find_opportunity_from_low_points(stock, low_points, latest_daily_record)
    
    def _find_lowest_records(self, stock: Dict[str, Any], monthly_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """寻找最低记录"""
        results = []
        
        if not monthly_records:
            return results
        
        # 按指定月数寻找最低点
        for term in self.terms:
            lowest_record = self._find_lowest_record(monthly_records, term)
            results.append({
                'code': stock['code'],
                'market': stock['market'],
                'last_for_months': term,
                'date_time': lowest_record['date'],
                'lowest_price': lowest_record['lowest']
            })
        
        # 寻找所有时间的最低点
        lowest_record = self._find_lowest_record(monthly_records)
        results.append({
            'code': stock['code'],
            'market': stock['market'],
            'last_for_months': 0,
            'date_time': lowest_record['date'],
            'lowest_price': lowest_record['lowest']
        })
        
        return results
    
    def _find_lowest_record(self, records: List[Dict[str, Any]], amount: Optional[int] = None) -> Dict[str, Any]:
        """寻找最低记录"""
        lowest_record = None
        
        # 从最新记录开始向前查找
        for i in range(len(records) - 1, -1, -1):
            if lowest_record is None:
                lowest_record = records[i]
            elif records[i]['lowest'] < lowest_record['lowest']:
                lowest_record = records[i]
            
            if amount and len(records) - i == amount:
                break
        
        return lowest_record
    
    def _find_opportunity_from_low_points(self, stock: Dict[str, Any], low_points: List[Dict[str, Any]], latest_daily_record: Dict[str, Any]) -> Dict[str, Any]:
        """从低点寻找机会"""
        result = {'is_opportunity': False}
        
        historic_low = self._is_in_invest_range(latest_daily_record, low_points)
        
        if historic_low:
            result['is_opportunity'] = True
            result['stock'] = stock
            result['goal'] = {
                'date': latest_daily_record['date'],
                'loss': self._set_loss(latest_daily_record),
                'win': self._set_win(latest_daily_record),
                'suggesting_purchase_price': latest_daily_record['close']
            }
            result['ref'] = historic_low
        
        return result
    
    def _is_in_invest_range(self, record: Dict[str, Any], low_points: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """判断是否在投资范围内"""
        for low in low_points:
            upper = low['lowest_price'] * (1 + self.goal['opportunity_range'])
            lower = low['lowest_price'] * (1 - self.goal['opportunity_range'])
            
            if lower <= record['close'] <= upper:
                return low
        
        return None
    
    def _set_loss(self, record: Dict[str, Any]) -> float:
        """设置止损价"""
        return record['close'] * self.goal['loss']
    
    def _set_win(self, record: Dict[str, Any]) -> float:
        """设置止盈价"""
        return record['close'] * self.goal['win']
    
    def _set_meta(self, suggestions: List[Dict[str, Any]]) -> None:
        """设置元数据"""
        try:
            caches = []
            for suggestion in suggestions:
                suggest = suggestion['result']
                cache = {
                    'c': suggest['stock']['code'],
                    'm': suggest['stock']['market'],
                    'n': suggest['stock']['name'],
                    'b': suggest['goal']['suggesting_purchase_price'],
                    'w': suggest['goal']['win'],
                    'l': suggest['goal']['loss'],
                    'hl': suggest['ref']['lowest_price'],
                    'hd': suggest['ref']['date_time'],
                    'ht': suggest['ref']['last_for_months']
                }
                caches.append(cache)
            
            # TODO: 保存到数据库
            logger.info(f"保存 {len(caches)} 个机会到元数据")
            
        except Exception as e:
            logger.error(f"设置元数据时出错: {e}")
    
    def _link_to_simulation_result(self, opportunity: Dict[str, Any]) -> None:
        """链接模拟结果"""
        try:
            if opportunity['result'].get('is_opportunity', False):
                stock = opportunity['result']['stock']
                # TODO: 从数据库获取模拟历史
                # simulate_history = self._get_stock_opportunity_summary(stock)
                # if simulate_history:
                #     opportunity['simulation'] = simulate_history
                pass
        except Exception as e:
            logger.error(f"链接模拟结果时出错: {e}")
    
    def _generate_report(self, opportunities: List[Dict[str, Any]]) -> str:
        """生成报告"""
        report_lines = []
        report_lines.append("=" * 100)
        report_lines.append(f"开始: {self.strategy_name} 在 {datetime.now().strftime('%Y-%m-%d')} 报告了 {len(opportunities)} 个机会")
        report_lines.append("=" * 100)
        
        for i, opportunity in enumerate(opportunities):
            result = opportunity['result']
            stock = opportunity['stock']
            simulation = opportunity.get('simulation')
            
            report_lines.append(f"------------> No.{i + 1}: {stock['name']} ({stock['code']}): <------------")
            report_lines.append(f"买入价格: {result['goal']['suggesting_purchase_price']:.2f} | 止损价: {result['goal']['loss']:.2f} | 止盈价: {result['goal']['win']:.2f}")
            
            if simulation:
                report_lines.append("\n------------> 模拟历史: <------------")
                report_lines.append(f"共进行了 {simulation['total']} 次模拟")
                report_lines.append(f"成功: {simulation['success']} | 失败: {simulation['fail']} | 还未触及目标: {simulation['open']}")
                report_lines.append(f"成功率: {simulation['success_rate']:.2%} | 失败率: {simulation['loss_rate']:.2%}")
                report_lines.append(f"当前策略的平均投资回报率: {simulation['average_roi']:.2%}")
                report_lines.append(f"当前策略的平均年化收益率: {simulation['annually_return']:.2%}")
                report_lines.append(f"当前策略的平均达到目标所持有时间为: {simulation['average_duration']}天")
                
                win_rate = simulation['success_rate']
                invest_portion = self._get_invest_portion_from_kelly_criterion(win_rate)
                report_lines.append(f"建议投入: 小于或等于投资总资产{invest_portion:.2%}的股票")
            else:
                report_lines.append("此股票是第一次发现当前策略下的机会。")
            
            report_lines.append("\n" + "-" * 50)
        
        report_lines.append("=" * 100)
        report_lines.append(f"总结: {self.strategy_name} 在 {datetime.now().strftime('%Y-%m-%d')} 报告了 {len(opportunities)} 个机会")
        report_lines.append("=" * 100)
        
        return "\n".join(report_lines)
    
    def _get_invest_portion_from_kelly_criterion(self, win_rate: float) -> float:
        """从凯利公式获取投资比例"""
        if win_rate < 0:
            return 0
        
        failure_rate = 1 - win_rate
        # 赔率
        odds = (self.goal['win'] - 1) / (self.goal['loss'] - 1)
        
        kelly_portion = (odds * win_rate - failure_rate) / odds
        return kelly_portion / self.goal['kelly_criterion_divider']
    
    def to_percent(self, num: float, digit: int = 2) -> str:
        """转换为百分比"""
        return f"{(num * 100):.{digit}f}%"
    
    def to_digit(self, num: float, digit: int = 2) -> str:
        """转换为指定小数位"""
        return f"{num:.{digit}f}" 