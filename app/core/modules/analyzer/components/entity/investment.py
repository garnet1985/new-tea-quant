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

        self.is_customized_take_profit = settings.get('goal', {}).get('take_profit', {}).get('is_customized', False)
        self.is_customized_stop_loss = settings.get('goal', {}).get('stop_loss', {}).get('is_customized', False)

        self.tracker = {
            'last_check_date': '',
            'targets_tracking': {},
        }

        self._create(settings, self.opportunity_ref.get('extra_fields', {}))


    def _create(self, settings: Dict[str, Any], extra_fields: Dict[str, Any]):
        # set up content
        self._set_up_content(extra_fields)

        # set up amplitude tracking
        self._set_up_amplitude_tracking()

        # set up targets tracking
        self._set_up_targets(settings, extra_fields)


    def _set_up_content(self, extra_fields: Dict[str, Any]):
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
            'amplitude_tracking': {},

            'extra_fields': extra_fields,
        }

    def _set_up_amplitude_tracking(self):
        self.content['amplitude_tracking'] = {
            'max_close_reached': { 'price': self.start_record_ref.get('close'), 'date': self.start_record_ref.get('date'), 'ratio': 0 },
            'min_close_reached': { 'price': self.start_record_ref.get('close'), 'date': self.start_record_ref.get('date'), 'ratio': 0 },
        }

    def _set_up_targets(self, settings: Dict[str, Any], extra_fields: Dict[str, Any]):
        """
        统一创建所有 targets 并按 priority 排序
        """
        targets = []
        targets_settings = settings.get('goal', {})
        
        # 1. Take Profit targets
        take_profit_settings = targets_settings.get('take_profit', {})
        if self.is_customized_take_profit:
            # Customized take profit
            customized_targets = self.strategy_class.create_customized_take_profit_targets(
                self.to_dict(), self.start_record_ref, extra_fields
            )
            for i, target in enumerate(customized_targets):
                target.is_customized = True
                target.priority = InvestmentTarget.TargetPriority.CUSTOMIZED_TAKE_PROFIT_BASE.value + i
                targets.append(target)
        else:
            # Normal take profit
            for i, stage in enumerate(take_profit_settings.get('stages', [])):
                target = InvestmentTarget(
                    target_type=InvestmentTarget.TargetType.TAKE_PROFIT,
                    start_record=self.start_record_ref,
                    stage=stage,
                    priority=InvestmentTarget.TargetPriority.NORMAL_TAKE_PROFIT_BASE.value + i
                )
                targets.append(target)
        
        # 2. Protect Loss - 初始未启用，但优先于普通止损
        protect_loss_settings = targets_settings.get('protect_loss')
        if protect_loss_settings:
            stage = InvestmentTarget.create_stage(
                name='protect_loss',
                target_settings=protect_loss_settings
            )
            protect_loss_target = InvestmentTarget(
                target_type=InvestmentTarget.TargetType.STOP_LOSS,
                start_record=self.start_record_ref,
                stage=stage,
                priority=InvestmentTarget.TargetPriority.PROTECT_LOSS.value,
                is_enabled=False
            )
            targets.append(protect_loss_target)
        
        # 3. Dynamic Loss - 初始未启用，但优先于普通止损
        dynamic_loss_settings = targets_settings.get('dynamic_loss')
        if dynamic_loss_settings:
            stage = InvestmentTarget.create_stage(
                name='dynamic_loss',
                target_settings=dynamic_loss_settings
            )
            dynamic_loss_target = InvestmentTarget(
                target_type=InvestmentTarget.TargetType.STOP_LOSS,
                start_record=self.start_record_ref,
                stage=stage,
                priority=InvestmentTarget.TargetPriority.DYNAMIC_LOSS.value,
                is_enabled=False
            )
            targets.append(dynamic_loss_target)
        
        # 4. Stop Loss targets
        stop_loss_settings = targets_settings.get('stop_loss', {})
        if self.is_customized_stop_loss:
            # Customized stop loss
            customized_targets = self.strategy_class.create_customized_stop_loss_targets(
                self.to_dict(), self.start_record_ref, extra_fields
            )
            for i, target in enumerate(customized_targets):
                target.is_customized = True
                target.priority = InvestmentTarget.TargetPriority.CUSTOMIZED_STOP_LOSS_BASE.value + i
                targets.append(target)
        else:
            # Normal stop loss
            for i, stage in enumerate(stop_loss_settings.get('stages', [])):
                target = InvestmentTarget(
                    target_type=InvestmentTarget.TargetType.STOP_LOSS,
                    start_record=self.start_record_ref,
                    stage=stage,
                    priority=InvestmentTarget.TargetPriority.NORMAL_STOP_LOSS_BASE.value + i
                )
                targets.append(target)
        
        # 5. Expiration
        fixed_period = settings.get('goal', {}).get('expiration', {}).get('fixed_period', 0)
        if fixed_period > 0:
            expiration_extra_fields = {
                'time_elapsed': 0,
                'fixed_period': fixed_period,
                'is_trading_period': settings.get('goal', {}).get('expiration', {}).get('is_trading_period', False),
                'term': settings.get('klines', {}).get('simulate_base_term', 'daily')
            }
            expiration_target = InvestmentTarget(
                target_type=InvestmentTarget.TargetType.EXPIRED,
                start_record=self.start_record_ref,
                stage={
                    'name': 'expiration',
                    'close_invest': True,
                },
                extra_fields=expiration_extra_fields,
                priority=InvestmentTarget.TargetPriority.EXPIRATION.value,
                is_enabled=True
            )
            targets.append(expiration_target)
        
        # 按 priority 排序
        targets.sort(key=lambda t: t.priority)
        
        # 保存到 tracker
        self.tracker['targets_tracking'] = {
            'remaining_investment_ratio': 1.0,
            'targets': targets
        }

    def is_completed(self, 
            record_of_today: Dict[str, Any],
            required_data: Dict[str, Any],
        )-> Tuple[bool, Dict[str, Any]]:
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
        is_investment_completed = self._check_targets(record_of_today, required_data)

        if is_investment_completed:
            self.settle(record_of_today)
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


    def _check_targets(self, record_of_today: Dict[str, Any], required_data: Dict[str, Any])-> bool:
        """
        统一检查所有 targets
        
        Args:
            record_of_today: 当前交易日记录
            required_data: 所需数据
        Returns:
            bool: 投资是否完成
        """
        if self._is_investment_complete():
            logger.warning(f"Investment is checked repeatedly, this warning shouldn't be triggered.")
            return False
        
        targets = self.tracker['targets_tracking']['targets']
        
        for target in targets:
            # 跳过未启用或已完成的 targets
            if not target.is_enabled or target.is_settled:
                continue
            
            is_target_achieved = False
            updated_remaining_investment_ratio = self.tracker['targets_tracking']['remaining_investment_ratio']
            
            # 根据 target 类型选择检查方法
            if target.content.get('name') == 'dynamic_loss':
                # Dynamic loss 特殊处理
                is_target_achieved, updated_remaining_investment_ratio = target.is_dynamic_loss_complete(
                    record_of_today,
                    self.tracker['targets_tracking']['remaining_investment_ratio']
                )
            
            elif target.target_type == InvestmentTarget.TargetType.EXPIRED:
                # Expiration 特殊处理
                is_expired = target.check_expiration(
                    record_of_today,
                    self.content['start_date']
                )
                if is_expired:
                    is_target_achieved = True
                    # Expiration 需要手动 settle
                    sell_ratio = target.calc_sell_ratio(updated_remaining_investment_ratio)
                    target.settle(record_of_today, sell_ratio)
                    updated_remaining_investment_ratio -= sell_ratio
            
            else:
                # 普通 targets（包括 customized）使用统一的 is_achieved()
                is_target_achieved, updated_remaining_investment_ratio = target.is_achieved(
                    record_of_today=record_of_today,
                    remaining_investment_ratio=self.tracker['targets_tracking']['remaining_investment_ratio'],
                    required_data=required_data,
                    strategy_class=self.strategy_class,
                    settings=self.settings,
                )
            
            # 处理 target 完成
            if is_target_achieved:
                self.tracker['targets_tracking']['remaining_investment_ratio'] = updated_remaining_investment_ratio
                self.content['completed_targets'].append(target.to_dict())
                self._trigger_actions(target, record_of_today)
            
            # 检查投资是否完成
            if self._is_investment_complete():
                return True
        
        return False



    def _trigger_actions(self, target: InvestmentTarget, record_of_today: Dict[str, Any]):
        """
        触发 target 完成后的 actions（启用 protect_loss 或 dynamic_loss）
        """
        if not target.has_actions():
            return
        
        actions = target.get_actions()
        all_targets = self.tracker['targets_tracking']['targets']
        
        for action in actions:
            if action == self.InvestmentGoalAction.SET_PROTECT_LOSS.value:
                # 查找并启用 protect_loss target
                for t in all_targets:
                    if t.content.get('name') == 'protect_loss':
                        t.is_enabled = True
                        # 记录触发信息
                        if t.tracker.get('extra_fields') is None:
                            t.tracker['extra_fields'] = {}
                        t.tracker['extra_fields']['triggered_by_target'] = target.content.get('name', '')
                        t.tracker['extra_fields']['triggered_by_action'] = action
                        logger.info(f"启用 protect_loss，由 {target.content.get('name')} 触发")
                        break
            
            elif action == self.InvestmentGoalAction.SET_DYNAMIC_LOSS.value:
                # 查找并启用 dynamic_loss target
                for t in all_targets:
                    if t.content.get('name') == 'dynamic_loss':
                        t.is_enabled = True
                        # Dynamic loss 需要使用触发它的 target 的 start_record
                        t.set_start_record(target.get_start_record())
                        # 记录触发信息
                        if t.tracker.get('extra_fields') is None:
                            t.tracker['extra_fields'] = {}
                        t.tracker['extra_fields']['triggered_by_target'] = target.content.get('name', '')
                        t.tracker['extra_fields']['triggered_by_action'] = action
                        logger.info(f"启用 dynamic_loss，由 {target.content.get('name')} 触发")
                        break



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
