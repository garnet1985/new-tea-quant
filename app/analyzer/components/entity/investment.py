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
                    'target': None,
                },
                'dynamic_loss': {
                    'is_enabled': False,
                    'last_highest_close': 0,
                    'target': None,
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

    def is_completed(self, record_of_today: Dict[str, Any])-> Tuple[bool, Dict[str, Any]]:
        """
        check investment and update investment tracking

        Args:
            record_of_today: record of today
        Returns:
            is_investment_completed: whether the investment is completed
            investment: investment
        """
        is_completed = False

        self._update_amplitude_tracking(record_of_today)
        is_investment_completed = self._check_targets(record_of_today)

        if is_investment_completed:
            is_completed = True
            self._settle(record_of_today)

        # check expiration
        if self.tracker['targets_tracking']['expiration']['is_enabled']:
            is_expired = self._check_expiration(record_of_today)
            if is_expired:
                is_completed = True
                self._settle(record_of_today)

        return is_completed, self.content


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


    def _check_targets(self, record_of_today: Dict[str, Any])-> bool:
        """
        check targets and update targets tracking

        Args:
            record_of_today: record of today
        Returns:
            is_investment_completed: whether the investment is completed
        """
        if self._is_investment_complete():
            return False
        
        take_profit_targets = self.tracker['targets_tracking']['take_profit']['targets']

        if self.is_customized_take_profit:
            # todo: use strategy class should take profit
            # is_investment_completed, achieved_targets = strategy_class.should_take_profit(record_of_today, self.content, self.tracker, self.settings)
            pass
        else:
            for target in take_profit_targets:
                target.check(record_of_today)

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
        self._check_protected_loss(record_of_today)
        self._check_dynamic_loss(record_of_today)
        self._check_normal_stop_loss_targets(record_of_today)

    def _check_protected_loss(self, record_of_today: Dict[str, Any]):
        if self.tracker['targets_tracking']['stop_loss']['protected_loss']['is_enabled']:
            target = self.tracker['targets_tracking']['stop_loss']['protected_loss']['target']
            if target.is_achieved(record_of_today):
                target.settle(record_of_today)
                self.tracker['targets_tracking']['completed'].append(target)

    def _check_dynamic_loss(self, record_of_today: Dict[str, Any]):
        if self.tracker['targets_tracking']['stop_loss']['dynamic_loss']['is_enabled']:
            target = self.tracker['targets_tracking']['stop_loss']['dynamic_loss']['target']
            tracking = self.tracker['targets_tracking']['stop_loss']['dynamic_loss']
            if target.is_dynamic_loss_achieved(record_of_today, tracking):
                target.settle(record_of_today)
                self.tracker['targets_tracking']['completed'].append(target)


    def _check_normal_stop_loss_targets(self, record_of_today: Dict[str, Any]):
        stop_loss_targets = self.tracker['targets_tracking']['stop_loss']['targets']
        for target in stop_loss_targets:
            if target.is_achieved(record_of_today):
                target.settle(record_of_today)
                if self._target_has_actions(target):
                    self._trigger_actions(target, record_of_today)
                    self.tracker['targets_tracking']['completed'].append(target)


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


    def _trigger_actions(self, target: InvestmentTarget, record_of_today: Dict[str, Any], settings: Dict[str, Any]):
        actions = target.content.get('actions')
        stop_loss_settings = settings.get('goal', {}).get('stop_loss', {})
        for action in actions:

            if action.get('name') == 'set_stop_loss':
                stop_loss_type = action.get('value')
                if stop_loss_type == 'protected' and stop_loss_settings.get('protected_loss', None) is not None:
                    self.tracker['targets_tracking']['stop_loss']['protected_loss']['is_enabled'] = True
                    
                    stage = InvestmentTarget.create_stage(
                        name='protected_loss',
                        target_settings = stop_loss_settings.get('protected_loss', {})
                    )

                    protected_loss_target = InvestmentTarget(InvestmentTarget.TargetType.STOP_LOSS, record_of_today, stage, 
                        extra_fields={
                            'is_triggered_by_action': True,
                            'triggered_by_action_name': target.content.get('name'),
                        }
                    )

                    self.tracker['targets_tracking']['stop_loss']['protected_loss']['target'] = protected_loss_target
                    
                elif stop_loss_type == 'dynamic' and stop_loss_settings.get('dynamic_loss', None) is not None:

                    self.tracker['targets_tracking']['stop_loss']['dynamic_loss']['is_enabled'] = True
                    self.tracker['targets_tracking']['stop_loss']['dynamic_loss']['last_highest_close'] = record_of_today.get('close')

                    stage = InvestmentTarget.create_stage(
                        name='dynamic_loss',
                        target_settings = stop_loss_settings.get('dynamic_loss', {})
                    )
                    dynamic_loss_target = InvestmentTarget(InvestmentTarget.TargetType.STOP_LOSS, record_of_today, stage, 
                        extra_fields={
                            'is_triggered_by_action': True,
                            'triggered_by_action_name': target.content.get('name'),
                        }
                    )

                    self.tracker['targets_tracking']['stop_loss']['dynamic_loss']['target'] = dynamic_loss_target
        # todo: add other actions

    def settle(self, record_of_today: Dict[str, Any], is_open: bool = False) -> Dict[str, Any]:
        """
        settle investment
        Args:
            record_of_today: record of today
            is_open: whether the investment is open
        Returns:
            investment: investment
        """
        self.content['end_date'] = record_of_today.get('date')

        total_profit = 0.0
        for target in self.tracker['targets_tracking']['completed']:
            total_profit += target['weighted_profit']

        roi = total_profit / self.content['purchase_price']



    # ================================ utils ================================
    def _is_investment_complete(self) -> bool:
        return self.tracker['targets_tracking']['remaining_investment_ratio'] <= 0


    def _get_sell_ratio(self, target: InvestmentTarget) -> float:
        if target.get('close_invest'):
            return self.tracker['targets_tracking']['remaining_investment_ratio']
        else:
            sell_ratio = target.get('sell_ratio')
            if sell_ratio > self.tracker['targets_tracking']['remaining_investment_ratio']:
                return self.tracker['targets_tracking']['remaining_investment_ratio']
            else:
                return sell_ratio

    def _target_has_actions(self, target: InvestmentTarget) -> bool:
        return len(target.content.get('actions', [])) > 0

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



# Investment
# │
# ├── __init__(record_of_today, opportunity, settings, strategy_class)
# │     ├── 保存初始参数
# │     ├── 初始化 tracker（追踪器）
# │     ├── 调用 _create() 初始化投资内容
# │
# ├── _create()
# │     ├── _set_up_content()         # 建立基本信息（价格、日期、股票）
# │     ├── _set_up_amplitude_tracking()  # 记录初始最大/最小价格
# │     ├── _set_up_targets()         # 创建止盈止损目标（InvestmentTarget）
# │
# ├── check(record_of_today)
# │     ├── 更新振幅追踪 → _update_amplitude_tracking()
# │     ├── 检查止盈止损目标 → _check_targets()
# │     │     ├── 止盈逻辑：
# │     │     │     ├── 若自定义 → 调用策略类 should_take_profit()
# │     │     │     └── 否则循环 target.check()
# │     │     ├── 止损逻辑：
# │     │     │     ├── 若自定义 → 调用策略类 should_stop_loss()
# │     │     │     └── 否则执行 _check_stop_loss_targets()
# │     │     │           ├── _check_protected_loss()
# │     │     │           ├── _check_dynamic_loss()
# │     │     │           └── _check_normal_stop_loss_targets()
# │     ├── 若达到任一目标 → _settle() 结算
# │     ├── 检查是否过期（_check_expiration()）
# │     └── 返回 (is_completed, content)
# │
# ├── _update_amplitude_tracking()
# │     ├── 记录当日收盘价变化
# │     ├── 更新 max/min close 及对应日期
# │
# ├── _check_stop_loss_targets()
# │     ├── _check_protected_loss()
# │     ├── _check_dynamic_loss()
# │     └── _check_normal_stop_loss_targets()
# │
# ├── _trigger_actions(target, record_of_today, settings)
# │     ├── 触发目标配置中的 actions，例如：
# │     │     └── set_stop_loss: 设置保护性止损或动态止损
# │
# ├── _check_expiration()
# │     ├── 检查持仓是否超出到期天数（交易日 / 自然日）
# │
# ├── _settle()
# │     ├── 记录结束日期、交易天数
# │     ├── 保存追踪信息（振幅、目标、止损状态等）
# │
# └── 工具函数
#       ├── _is_investment_complete()  # 判断是否已清仓
#       ├── _get_sell_ratio()          # 计算卖出比例
#       └── _has_actions()             # 判断目标是否带有后续动作