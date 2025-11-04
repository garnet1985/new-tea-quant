from enum import Enum
from typing import Any, Dict, List, Tuple

from loguru import logger
from app.analyzer.components.entity.target import InvestmentTarget
from utils.date.date_utils import DateUtils
from utils.icon.icon_service import IconService 


class Investment:

    class InvestmentResult(Enum):
        WIN = 'win'
        LOSS = 'loss'
        OPEN = 'open'

    class InvestmentGoalAction(Enum):
        SET_PROTECT_LOSS = 'set_protect_loss'
        SET_DYNAMIC_LOSS = 'set_dynamic_loss'

    def __init__(self, 
        start_record: Dict[str, Any],
        opportunity: Dict[str, Any],
        settings: Dict[str, Any],
        strategy_class: Any,
    ):
        self.is_settled = False

        self.start_record_ref = start_record
        self.settings = settings
        self.strategy_class = strategy_class

        self.opportunity_ref = opportunity.to_dict()
        self.content = {}

        self.tracker = {
            'last_check_date': '',
            'targets_tracking': {},
        }

        self._create(settings)


    def _create(self, settings: Dict[str, Any]):
        # set up content
        self._set_up_content()

        # set up amplitude tracking
        self._set_up_amplitude_tracking()

        # set up targets tracking
        self._set_up_targets(settings)


    def _set_up_content(self):
        purchase_price = self.start_record_ref.get('close')
        purchase_date = self.start_record_ref.get('date')

        self.content = {
            'result': None,
            'roi': None,
            'overall_profit': None,
            'duration_in_days': None,
            'duration_in_trading_days': None,

            'purchase_price': purchase_price,
            'start_date': purchase_date,
            'end_date': None,
            'completed_targets': [],
            'amplitude_tracking': {}
        }

    def _set_up_amplitude_tracking(self):
        self.content['amplitude_tracking'] = {
            'max_close_reached': { 'price': self.start_record_ref.get('close'), 'date': self.start_record_ref.get('date'), 'ratio': 0 },
            'min_close_reached': { 'price': self.start_record_ref.get('close'), 'date': self.start_record_ref.get('date'), 'ratio': 0 },
        }

    def _set_up_targets(self, settings: Dict[str, Any]):
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
                'protect_loss': {
                    'is_enabled': False,
                    'target': None,
                },
                'dynamic_loss': {
                    'is_enabled': False,
                    'target': None,
                },
            },
            'expiration': {
                'is_enabled': False,
                'fixed_period': 0,
                'is_trading_period': True,
                'time_elapsed': 0,
                'term': 'daily'
            },
        }

        targets_settings = settings.get('goal', {})
        take_profit_settings = targets_settings.get('take_profit', {})
        self.is_customized_take_profit = take_profit_settings.get('is_customized', False)
        if not self.is_customized_take_profit:
            for stage in take_profit_settings.get('stages', []):
                self.tracker['targets_tracking']['take_profit']['targets'].append(
                    InvestmentTarget(
                        target_type=InvestmentTarget.TargetType.TAKE_PROFIT, 
                        start_record=self.start_record_ref, 
                        stage=stage
                    )
                )

        stop_loss_settings = targets_settings.get('stop_loss', {})
        self.is_customized_stop_loss = stop_loss_settings.get('is_customized', False)
        if not self.is_customized_stop_loss:
            for stage in stop_loss_settings.get('stages', []):
                self.tracker['targets_tracking']['stop_loss']['targets'].append(
                    InvestmentTarget(
                        target_type=InvestmentTarget.TargetType.STOP_LOSS, 
                        start_record=self.start_record_ref, 
                        stage=stage
                    )
                )

        fixed_period = settings.get('goal', {}).get('expiration', {}).get('fixed_period', 0)  
        if fixed_period > 0:
            self.tracker['targets_tracking']['expiration']['is_enabled'] = True
            self.tracker['targets_tracking']['expiration']['fixed_period'] = fixed_period
            self.tracker['targets_tracking']['expiration']['is_trading_period'] = settings.get('goal', {}).get('expiration', {}).get('is_trading_period', False)
            self.tracker['targets_tracking']['expiration']['term'] = settings.get('goal', {}).get('klines', {}).get('simulation_base_term', 'daily')
            self.tracker['targets_tracking']['expiration']['time_elapsed'] = 0

    def is_completed(self, record_of_today: Dict[str, Any])-> Tuple[bool, Dict[str, Any]]:
        """
        check investment and update investment tracking
        如果投资完成，立即settle并返回settled字典

        Args:
            record_of_today: record of today
        Returns:
            is_investment_completed: whether the investment is completed
            investment: settled investment dict if completed, else content
        """

        self._update_amplitude_tracking(record_of_today)
        is_investment_completed = self._check_targets(record_of_today)

        if is_investment_completed:
            self.settle(record_of_today)
            return True, self.to_dict()
        # check expiration
        if self.tracker['targets_tracking']['expiration']['is_enabled']:
            is_expired = self._check_expiration(record_of_today)
            if is_expired:
                self.settle_by_expiration(record_of_today)
                return True, self.to_dict()
        return False, None


    def _update_amplitude_tracking(self, record_of_today: Dict[str, Any]):
        date = record_of_today.get('date', '')
        last_check_date = self.tracker.get('last_check_date')
        if date <= last_check_date:
            return

        close_price = record_of_today.get('close')
        purchase_price = self.start_record_ref.get('close', 0)
        self.tracker['last_check_date'] = date
        
        amplitude_tracking = self.content['amplitude_tracking']
        if close_price >= amplitude_tracking['max_close_reached']['price']:
            amplitude_tracking['max_close_reached']['price'] = close_price
            amplitude_tracking['max_close_reached']['date'] = date
            amplitude_tracking['max_close_reached']['ratio'] = (close_price - purchase_price) / purchase_price if purchase_price > 0 else 0
            
        if close_price < amplitude_tracking['min_close_reached']['price']:
            amplitude_tracking['min_close_reached']['price'] = close_price
            amplitude_tracking['min_close_reached']['date'] = date
            amplitude_tracking['min_close_reached']['ratio'] = (close_price - purchase_price) / purchase_price if purchase_price > 0 else 0


    def _check_targets(self, record_of_today: Dict[str, Any])-> bool:
        """
        check targets and update targets tracking

        Args:
            record_of_today: record of today
        Returns:
            is_investment_completed: whether the investment is completed
        """
        if self._is_investment_complete():
            logger.warning(f"Investment is checked repeatedly, this warning shouldn't be triggered.")
            return False
        
        take_profit_targets = self.tracker['targets_tracking']['take_profit']['targets']

        if self.is_customized_take_profit:
            # todo: use strategy class should take profit
            # is_investment_completed, achieved_targets = strategy_class.should_take_profit(record_of_today, self.content, self.tracker, self.settings)
            pass
        else:
            for target in take_profit_targets:
                if target.is_achieved:
                    continue
                is_target_completed, remaining_investment_ratio = target.is_complete(record_of_today, self.tracker['targets_tracking']['remaining_investment_ratio'])
                if is_target_completed:
                    self.tracker['targets_tracking']['remaining_investment_ratio'] = remaining_investment_ratio
                    self.content['completed_targets'].append(target.to_dict())
                    self._trigger_actions(target, record_of_today)

            # if all take profit targets are achieved, the investment is completed
            if self._is_investment_complete():
                return True

        if self.is_customized_stop_loss:
            # todo: use strategy class should stop loss
            # is_investment_completed, achieved_targets = strategy_class.should_stop_loss(record_of_today, self.content, self.tracker, self.settings)
            pass
        else:
            self._check_stop_loss_targets(record_of_today)

            # if all stop loss targets are achieved, the investment is completed
            if self._is_investment_complete():
                return True

        return False

    def _check_stop_loss_targets(self, record_of_today: Dict[str, Any]):
        self._check_protect_loss(record_of_today)
        self._check_dynamic_loss(record_of_today)
        self._check_normal_stop_loss_targets(record_of_today)

    def _check_protect_loss(self, record_of_today: Dict[str, Any]):
        protect_loss_info = self.tracker['targets_tracking']['stop_loss']['protect_loss']
        target = protect_loss_info['target']
        if protect_loss_info['is_enabled'] and target.is_achieved is not True:
            is_target_completed, remaining_investment_ratio = target.is_complete(
                record_of_today, 
                self.tracker['targets_tracking']['remaining_investment_ratio']
            )
            if is_target_completed:    
                self.tracker['targets_tracking']['remaining_investment_ratio'] = remaining_investment_ratio
                self.content['completed_targets'].append(target.to_dict())

    def _check_dynamic_loss(self, record_of_today: Dict[str, Any]):
        dynamic_loss_info = self.tracker['targets_tracking']['stop_loss']['dynamic_loss']
        target = dynamic_loss_info['target']
        if dynamic_loss_info['is_enabled'] and target.is_achieved is not True:
            is_target_completed, remaining_investment_ratio = target.is_dynamic_loss_complete(
                record_of_today, 
                self.tracker['targets_tracking']['remaining_investment_ratio']
            )
            if is_target_completed:
                self.tracker['targets_tracking']['remaining_investment_ratio'] = remaining_investment_ratio
                self.content['completed_targets'].append(target.to_dict())


    def _check_normal_stop_loss_targets(self, record_of_today: Dict[str, Any]):
        stop_loss_targets = self.tracker['targets_tracking']['stop_loss']['targets']
        for target in stop_loss_targets:
            if target.is_achieved:
                continue
            is_target_completed, remaining_investment_ratio = target.is_complete(record_of_today, self.tracker['targets_tracking']['remaining_investment_ratio'])
            if is_target_completed:
                self.tracker['targets_tracking']['remaining_investment_ratio'] = remaining_investment_ratio
                self.content['completed_targets'].append(target.to_dict())
                self._trigger_actions(target, record_of_today)

    def _check_expiration(self, record_of_today: Dict[str, Any])-> bool:
        if not self.tracker['targets_tracking']['expiration']['is_enabled']:
            return False
        
        if self.tracker['targets_tracking']['expiration']['is_trading_period']:
            # counting time by trading term unit
            self.tracker['targets_tracking']['expiration']['time_elapsed'] += 1
            if self.tracker['targets_tracking']['expiration']['time_elapsed'] >= self.tracker['targets_tracking']['expiration']['fixed_period']:
                return True
        else:
            # counting time by natural term unit
            date_of_today = record_of_today.get('date')
            date_of_start = self.content['start_date']
            elapsed_natural_period = DateUtils.get_duration_by_term(self.tracker['targets_tracking']['expiration']['term'], date_of_start, date_of_today)
            if elapsed_natural_period >= self.tracker['targets_tracking']['expiration']['fixed_period']:
                return True
        return False


    def _trigger_actions(self, target: InvestmentTarget, record_of_today: Dict[str, Any]):
        # this should be triggered after target is completed
        if target.has_actions() is False:
            return
        goal_settings = self.settings.get('goal', {})
        actions = target.get_actions()
        for action in actions:
            if action == self.InvestmentGoalAction.SET_PROTECT_LOSS.value and goal_settings.get('protect_loss', None) is not None:
                self._enable_protect_loss(target)

            if action == self.InvestmentGoalAction.SET_DYNAMIC_LOSS.value and goal_settings.get('dynamic_loss', None) is not None:
                self._enable_dynamic_loss(record_of_today, target)


    def _enable_protect_loss(self, just_completed_target: InvestmentTarget):
        self.tracker['targets_tracking']['stop_loss']['protect_loss']['is_enabled'] = True
        protect_loss_settings = self.settings.get('goal', {}).get('protect_loss', {})
        
        stage = InvestmentTarget.create_stage(
            name='protect_loss',
            target_settings = protect_loss_settings
        )
        
        protect_loss_target = InvestmentTarget(InvestmentTarget.TargetType.STOP_LOSS, self.start_record_ref, stage, 
            extra_fields={
                'triggered_by_target': just_completed_target.to_dict().get('name', ''),
                'triggered_by_action': self.InvestmentGoalAction.SET_PROTECT_LOSS.value,
            }
        )

        self.tracker['targets_tracking']['stop_loss']['protect_loss']['target'] = protect_loss_target

    def _enable_dynamic_loss(self, record_of_today: Dict[str, Any], just_completed_target: InvestmentTarget):
        self.tracker['targets_tracking']['stop_loss']['dynamic_loss']['is_enabled'] = True
        dynamic_loss_settings = self.settings.get('goal', {}).get('dynamic_loss', {})
        
        stage = InvestmentTarget.create_stage(
            name='dynamic_loss',
            target_settings = dynamic_loss_settings
        )

        dynamic_loss_target = InvestmentTarget(InvestmentTarget.TargetType.STOP_LOSS, record_of_today, stage, 
            extra_fields={
                'triggered_by_target': just_completed_target.to_dict().get('name', ''),
                'triggered_by_action': self.InvestmentGoalAction.SET_DYNAMIC_LOSS.value,
            }
        )

        real_start_record = just_completed_target.get_start_record()
        dynamic_loss_target.set_start_record(real_start_record)
        self.tracker['targets_tracking']['stop_loss']['dynamic_loss']['target'] = dynamic_loss_target


    def settle_by_expiration(self, record_of_today: Dict[str, Any]):
        """
        settle investment by expiration
        """
        extra_fields = {
            'expired_term': f"{self.tracker['targets_tracking']['expiration']['term']}",
            'counting_by': "trading" if self.tracker['targets_tracking']['expiration']['is_trading_period'] else "natural",
            'elapsed_time': f"{self.tracker['targets_tracking']['expiration']['time_elapsed']}",
            'elapsed_time_in_days': DateUtils.get_duration_in_days(
                self.content['start_date'],
                record_of_today.get('date'),
                DateUtils.DATE_FORMAT_YYYYMMDD
            ),
        }

        expire_target = InvestmentTarget(
            target_type=InvestmentTarget.TargetType.EXPIRED,
            start_record=self.start_record_ref,
            stage=InvestmentTarget.create_stage(
                name='expiration',
                target_settings={
                    **self.tracker['targets_tracking']['expiration'],
                    'close_invest': True,
                }
            ),
            extra_fields=extra_fields
        )
        expire_target.settle(record_of_today, expire_target.calc_sell_ratio(self.tracker['targets_tracking']['remaining_investment_ratio']))
        self.content['completed_targets'].append(expire_target.to_dict())
        self.tracker['targets_tracking']['remaining_investment_ratio'] = 0
        self.settle(record_of_today)

    def settle(self, record_of_today: Dict[str, Any], is_open: bool = False):
        """
        settle investment
        Args:
            record_of_today: record of today
            is_open: whether the investment is open
        Returns:
            investment: settled investment as dict
        """
        
        if self.is_settled:
            logger.warning(f"Investment already settled, check logic, this warning shouldn't be triggered.")
            return
        
        self.is_settled = True
        self.content['end_date'] = record_of_today.get('date')

        if is_open:
            # create an open target to track the uncompleted investment
            uncompleted_target = InvestmentTarget(
                target_type=InvestmentTarget.TargetType.OPEN,
                start_record=self.start_record_ref,
                stage=InvestmentTarget.create_stage(
                    name='open',
                    target_settings={
                        'close_invest': True,
                    }
                )
            )
            uncompleted_target.settle(record_of_today, uncompleted_target.calc_sell_ratio(self.tracker['targets_tracking']['remaining_investment_ratio']))
            self.content['completed_targets'].append(uncompleted_target.to_dict())


        # calculate overall profit & ROI
        total_profit = 0.0
        for target in self.content['completed_targets']:
            weighted_profit = target.get('weighted_profit', 0)
            total_profit += weighted_profit
        self.content['overall_profit'] = total_profit


        roi = self.content['overall_profit'] / self.content['purchase_price'] if self.content['purchase_price'] > 0 else 0
        self.content['roi'] = roi
        
        # mark result
        icon = "";
        invest_res_str = "";
        if is_open:
            icon = IconService.get('ongoing')
            result = self.InvestmentResult.OPEN.value
            invest_res_str = "未完成"
        elif roi > 0:
            icon = IconService.get('success')
            result = self.InvestmentResult.WIN.value
            invest_res_str = "成功"
        else:
            icon = IconService.get('error')
            result = self.InvestmentResult.LOSS.value
            invest_res_str = "失败"
        self.content['result'] = result
        
        # Calculate invest duration
        invest_duration_days = DateUtils.get_duration_in_days(
            self.content['start_date'], 
            self.content['end_date'], 
            DateUtils.DATE_FORMAT_YYYYMMDD
        ) if self.content.get('end_date') else 0

        self.content['duration_in_days'] = invest_duration_days

        stock = self.opportunity_ref.get('stock', {})
        logger.info(f"{icon} {stock.get('name', '')} ({stock.get('id', '')}) 投资{invest_res_str}，ROI:{roi*100:.2f}%，持续时间: {invest_duration_days}个自然日")
        

    def to_dict(self) -> Dict[str, Any]:
        return self.content



    # ================================ utils ================================
    def _is_investment_complete(self) -> bool:
        return self.tracker['targets_tracking']['remaining_investment_ratio'] <= 0
