from enum import Enum
from typing import Any, Dict, List, Tuple
from app.analyzer.components.entity.target import InvestmentTarget
from utils.date.date_utils import DateUtils 


class Investment:

    class InvestmentResult(Enum):
        WIN = 'win'
        LOSS = 'loss'
        OPEN = 'open'

    def __init__(self, 
        record_of_today: Dict[str, Any],
        opportunity: Dict[str, Any],
        settings: Dict[str, Any],
        strategy_class: Any,
    ):
        self.start_record_ref = record_of_today
        self.settings = settings
        self.strategy_class = strategy_class

        self.content = {}

        self.tracker = {
            'last_check_date': '',
            'targets_tracking': {},
        }

        self._create(record_of_today, opportunity, settings)


    def _create(self, record_of_today: Dict[str, Any], opportunity: Dict[str, Any], settings: Dict[str, Any]):
        # set up content
        self._set_up_content(record_of_today, opportunity)

        # set up amplitude tracking
        self._set_up_amplitude_tracking(record_of_today)

        # set up targets tracking
        self._set_up_targets(record_of_today, settings)


    def _set_up_content(self, record_of_today: Dict[str, Any], opportunity: Dict[str, Any]):
        purchase_price = record_of_today.get('close')
        purchase_date = record_of_today.get('date')

        self.content = {
            'stock': opportunity.get('stock', {}),
            'opportunity_ref': opportunity,
            'purchase_price': purchase_price,
            'start_date': purchase_date,
            'end_date': '',
            'trading_days': 0,
        }

    def _set_up_amplitude_tracking(self, record_of_today: Dict[str, Any]):
        self.content['amplitude_tracking'] = {
            'max_close_reached': { 'price': record_of_today.get('close'), 'date': record_of_today.get('date'), 'ratio': 0 },
            'min_close_reached': { 'price': record_of_today.get('close'), 'date': record_of_today.get('date'), 'ratio': 0 },
        }

    def _set_up_targets(self, record_of_today: Dict[str, Any], settings: Dict[str, Any]):
        self.tracker['targets_tracking'] = {
            'remaining_investment_ratio': 1.0,
            'completed': [],
            'take_profit': {
                'is_customized': False,
                'targets': [],
            },
            'stop_loss': {
                'is_customized': False,
                'targets': [],
                'protected_loss': {
                    'is_enabled': False,
                    'target_price': 0,
                },
                'dynamic_loss': {
                    'is_enabled': False,
                    'last_highest_close': 0,
                },
            },
            'expiration': {
                'is_enabled': False,
                'fixed_days': 0,
                'is_trading_days': True,
                'elapsed_trading_days': 0,
                'elapsed_natural_days': 0,
            },
        }

        targets_settings = settings.get('goal', {})
        take_profit_settings = targets_settings.get('take_profit', {})
        self.is_customized_take_profit = take_profit_settings.get('is_customized', False)
        if not self.is_customized_take_profit:
            for stage in take_profit_settings.get('stages', []):
                self.tracker['targets_tracking']['take_profit']['targets'].append(InvestmentTarget(InvestmentTarget.TargetType.TAKE_PROFIT, record_of_today, stage))

        stop_loss_settings = targets_settings.get('stop_loss', {})
        self.is_customized_stop_loss = stop_loss_settings.get('is_customized', False)
        if not self.is_customized_stop_loss:
            for stage in stop_loss_settings.get('stages', []):
                self.tracker['targets_tracking']['stop_loss']['targets'].append(InvestmentTarget(InvestmentTarget.TargetType.STOP_LOSS, record_of_today, stage))


    def check(self, record_of_today: Dict[str, Any]):
        self._update_amplitude_tracking(record_of_today)
        self._check_targets(record_of_today)


    def _update_amplitude_tracking(self, record_of_today: Dict[str, Any]):
        date = record_of_today.get('date', '')
        last_check_date = self.tracker.get('last_check_date')
        if date <= last_check_date:
            return

        close_price = record_of_today.get('close')
        self.tracker['last_check_date'] = date
        if close_price >= self.amplitude_tracking['max_close_reached']['price']:
            self.amplitude_tracking['max_close_reached']['price'] = close_price
            self.amplitude_tracking['max_close_reached']['date'] = date
            self.amplitude_tracking['max_close_reached']['ratio'] = (close_price - self.start_record_ref.get('close', 0)) / self.start_record_ref.get('close', 0)
            
        if close_price < self.amplitude_tracking['min_close_reached']['price']:
            self.amplitude_tracking['min_close_reached']['price'] = close_price
            self.amplitude_tracking['min_close_reached']['date'] = date
            self.amplitude_tracking['min_close_reached']['ratio'] = (close_price - self.start_record_ref.get('close', 0)) / self.start_record_ref.get('close', 0)


    def _check_targets(self, targets_tracking: Dict[str, Any], record_of_today: Dict[str, Any])-> Tuple[bool, Dict[str, Any]]:
        if self._is_investment_complete():
            return True, self._settle(record_of_today)
        
        take_profit_targets = targets_tracking['take_profit']['targets']
        stop_loss_targets = targets_tracking['stop_loss']['targets']

        if self.is_customized_take_profit:
            # todo: use strategy class should take profit
            # should_close_investment, achieved_targets = strategy_class.should_take_profit(record_of_today, self.content, self.tracker, self.settings)
            pass
        else:
            for target in take_profit_targets:
                target.check(record_of_today)

            if self._is_investment_complete():
                return True, self._settle(record_of_today)

        if self.is_customized_stop_loss:
            # todo: use strategy class should stop loss
            # should_close_investment, achieved_targets = strategy_class.should_stop_loss(record_of_today, self.content, self.tracker, self.settings)
            pass
        else:
            should_close_investment = self._check_stop_loss_targets(stop_loss_targets, record_of_today)
            if should_close_investment:
                return True, self._settle(record_of_today)

        if self.tracker['targets_tracking']['expiration']['is_enabled']:
            should_close_investment = self._check_expiration(record_of_today)
            if should_close_investment:
                return True, self._settle(record_of_today)

        return False, None

    def _check_stop_loss_targets(self, targets: List[InvestmentTarget], record_of_today: Dict[str, Any]):
        if self.tracker['targets_tracking']['stop_loss']['protected_loss']['is_enabled']:
            target = self.tracker['targets_tracking']['stop_loss']['protected_loss']['target']
            is_achieved = self._check_protected_loss(targets, record_of_today)
            if is_achieved:
                target.settle(record_of_today)
                self.tracker['targets_tracking']['completed'].append(target)
                return True

        if self.tracker['targets_tracking']['stop_loss']['dynamic_loss']['is_enabled']:
            target = self.tracker['targets_tracking']['stop_loss']['dynamic_loss']['target']
            is_achieved = self._check_dynamic_loss(targets, record_of_today)
            if is_achieved:
                target.settle(record_of_today)
                self.tracker['targets_tracking']['completed'].append(target)
                return True
    
        for target in targets:
            is_achieved, target.check(record_of_today)
            if is_achieved:
                target.settle(record_of_today)
                self.tracker['targets_tracking']['completed'].append(target)
                
        return self._is_investment_complete()

    def _check_protected_loss(self, targets: List[InvestmentTarget], record_of_today: Dict[str, Any]):
        if self.tracker['targets_tracking']['stop_loss']['protected_loss']['is_enabled']:
            # todo: use strategy class should protected loss
            pass
        else:
            for target in targets:
                target.check(record_of_today)

    def _check_dynamic_loss(self, targets: List[InvestmentTarget], record_of_today: Dict[str, Any]):
        if self.tracker['targets_tracking']['stop_loss']['dynamic_loss']['is_enabled']:
            # todo: use strategy class should dynamic loss
            pass
        else:
            for target in targets:
                target.check(record_of_today)


    def _check_expiration(self, record_of_today: Dict[str, Any])-> bool:
        if not self.tracker['targets_tracking']['expiration']['is_enabled']:
            return False
        
        if self.tracker['targets_tracking']['expiration']['is_trading_days']:
            self.tracker['targets_tracking']['expiration']['elapsed_trading_days'] += 1
            if self.tracker['targets_tracking']['expiration']['elapsed_trading_days'] >= self.tracker['targets_tracking']['expiration']['fixed_days']:
                return True
        else:
            date_of_today = record_of_today.get('date')
            date_of_start = self.content['start_date']
            elapsed_natural_days = DateUtils.get_duration_in_days(date_of_start, date_of_today, DateUtils.DATE_FORMAT_YYYYMMDD)
            if elapsed_natural_days >= self.tracker['targets_tracking']['expiration']['fixed_days']:
                return True
        return False

    def _is_investment_complete(self) -> bool:
        return self.tracker['targets_tracking']['remaining_investment_ratio'] <= 0

    def _settle(self, record_of_today: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        if self._is_investment_complete():
            self.content['end_date'] = record_of_today.get('date')
            self.content['trading_days'] = self.tracker['expiration']['elapsed_trading_days']
            self.content['amplitude_tracking'] = self.amplitude_tracking
            self.content['target_tracking'] = self.tracker['target_tracking']
            self.content['dynamic_loss'] = self.tracker['dynamic_loss']
            self.content['expiration'] = self.tracker['expiration']
            return True, self.content
        else:
            return False, self.content

    def _get_sell_ratio(self, target: InvestmentTarget) -> float:
        if target.get('close_invest'):
            return self.tracker['targets_tracking']['remaining_investment_ratio']
        else:
            sell_ratio = target.get('sell_ratio')
            if sell_ratio > self.tracker['targets_tracking']['remaining_investment_ratio']:
                return self.tracker['targets_tracking']['remaining_investment_ratio']
            else:
                return sell_ratio


    # @staticmethod
    # def to_settled_investment(record_of_today: Dict[str, Any], investment: Dict[str, Any], is_open: bool = False) -> Dict[str, Any]:
    #     """
    #     将投资转换为已结算投资（统一结算逻辑）。
    #     - 根据 completed targets 计算总体收益与 ROI
    #     - 设置结果枚举（WIN/LOSS/OPEN）
    #     - 计算持有时长、年化收益
    #     - 最后交由策略可选地调整结构（to_alt_settled_investment）
    #     """
    #     completed_targets = (investment.get('targets_tracking', {}).get('completed', []) or [])
    #     overall_profit = 0.0
    #     investment['end_date'] = record_of_today.get('date')

    #     for target in completed_targets:
    #         target['weighted_profit'] = float(target.get('profit', 0.0)) * float(target.get('sell_ratio', 0.0))
    #         target['profit_contribution'] = float(target.get('sell_ratio', 0.0))
    #         overall_profit += target['weighted_profit']

    #     icon = ''
    #     if overall_profit >= 0:
    #         investment['result'] = InvestmentResult.WIN.value
    #         icon = IconService.get('check') + ' 投资成功'
    #     else:
    #         investment['result'] = InvestmentResult.LOSS.value
    #         icon = IconService.get('cross') + ' 投资失败'

    #     if is_open:
    #         investment['result'] = InvestmentResult.OPEN.value
    #         icon = IconService.get('ongoing') + ' 投资未完成'

    #     investment['overall_profit'] = overall_profit
    #     # ROI 使用小数格式（如 0.20 = 20%）
    #     investment['overall_profit_rate'] = AnalyzerService.to_ratio(overall_profit, investment['purchase_price'], decimals=4)
    #     purchase_date = investment.get('start_date') or investment.get('purchase_date') or ''
    #     end_date = investment.get('end_date') or record_of_today.get('date') or ''
    #     investment['invest_duration_days'] = AnalyzerService.get_duration_in_days(purchase_date, end_date) if purchase_date and end_date else 0
    #     overall_annual_return_raw = AnalyzerService.get_annual_return(investment['overall_profit_rate'], investment['invest_duration_days'])
    #     investment['overall_annual_return'] = float(overall_annual_return_raw.real) if isinstance(overall_annual_return_raw, complex) else float(overall_annual_return_raw) if isinstance(overall_annual_return_raw, (int, float)) else 0.0

    #     logger.info(f"{icon}: {investment['stock']['name']} ({investment['stock']['id']}) - ROI: {investment['overall_profit_rate'] * 100:.2f}% in {investment['invest_duration_days']} days")

    #     return investment













    # @staticmethod
    # def create_investment(
    #         record_of_today: Dict[str, Any],
    #         opportunity: Dict[str, Any],
    #         settings: Dict[str, Any],
    #     ) -> Dict[str, Any]:
            
    #     """
    #     构建标准投资实体（构建职责专一）。
    #     """
    #     purchase_price = record_of_today.get('close')
    #     purchase_date = record_of_today.get('date')

    #     # base structure
    #     investment: Dict[str, Any] = {
    #         'stock': opportunity.get('stock', {}),
    #         'opportunity_ref': opportunity,
    #         'purchase_price': purchase_price,
    #         'start_date': purchase_date,
    #         'end_date': '',
    #     }

    #     # amplitude tracking: max/min close reached - should go into each target
    #     # amplitude_tracking: Dict[str, Any] = {
    #     #     'max_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
    #     #     'min_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
    #     # }

    #     # investment['amplitude_tracking'] = amplitude_tracking

    #     # tracking targets
    #     target_tracking: Dict[str, Any] = {
    #         'investment_ratio_left': 1.0,
    #         'completed': [],
    #         'protected_loss': {
    #             'is_enabled': False,
    #             'target_price': purchase_price * (1 + settings.get('goal', {}).get('stop_loss', {}).get('break_even', {}).get('ratio', 0)),
    #         },
    #         'dynamic_loss': {
    #             'is_enabled': False,
    #             'last_highest_close': 0.0,
    #             'ratio': settings.get('goal', {}).get('stop_loss', {}).get('dynamic', {}).get('ratio', -0.1),
    #         },
    #         'expiration': {
    #             'is_enabled': False,
    #             'fixed_days': settings.get('goal', {}).get('fixed_days', 0),
    #             'is_trading_days': settings.get('goal', {}).get('is_trading_days', True),
    #             'elapsed_trading_days': 0,
    #             'elapsed_natural_days': 0,
    #             'start_date': purchase_date,
    #             'end_date': '',
    #         }
    #     }

    #     if BaseStrategy.is_customized_stop_loss(settings):
    #         target_tracking['stop_loss'] = {
    #             'is_customized': True,
    #             'targets': BaseStrategy.create_customized_targets(BaseStrategy.TargetType.STOP_LOSS.value, record_of_today),
    #         }
    #     else:
    #         target_tracking['stop_loss'] = {
    #             'is_customized': False,
    #             'targets': BaseStrategy.create_targets(BaseStrategy.TargetType.STOP_LOSS, record_of_today, settings.get('goal', {}).get('stop_loss')),
    #         }

            
    #     if BaseStrategy.is_customized_take_profit(settings):
    #         target_tracking['take_profit'] = {
    #             'is_customized': True,
    #             'targets': BaseStrategy.create_customized_targets(BaseStrategy.TargetType.TAKE_PROFIT.value, record_of_today),
    #         }
    #     else:
    #         target_tracking['take_profit'] = {
    #             'is_customized': False,
    #             'targets': BaseStrategy.create_targets(BaseStrategy.TargetType.TAKE_PROFIT, record_of_today, settings.get('goal', {}).get('take_profit')),
    #         }

    #     investment['targets_tracking'] = target_tracking

    #     # TODO: debug:
    #     print(target_tracking)


    #     # 透传策略自定义字段（如 momentum 等）
    #     extra_fields = opportunity.get('extra_fields')

    #     if extra_fields:
    #         investment['extra_fields'] = extra_fields

    #     return investment