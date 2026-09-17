import { formatGoalSummaryLines } from './strategyGoal';

describe('formatGoalSummaryLines', () => {
  it('turns take-profit and stop-loss stages into full Chinese sentences', () => {
    expect(formatGoalSummaryLines({
      take_profit: {
        stages: [
          { ratio: 0.15, exit_ratio: 0.3 },
          { ratio: 0.25, close_invest: true },
        ],
      },
      stop_loss: {
        stages: [{ ratio: -0.2, close_invest: true }],
      },
    })).toEqual([
      '止盈：当盈利 15% 卖出 30%；当盈利 25% 清仓',
      '止损：当亏损 20% 清仓',
    ]);
  });

  it('includes hold window, protect loss and dynamic loss', () => {
    expect(formatGoalSummaryLines({
      expiration: { fixed_window_in_days: 30, mode: 'trading_day' },
      take_profit: {
        stages: [
          { ratio: 0.15, exit_ratio: 0.3, actions: ['set_protect_loss'] },
          { ratio: 0.25, close_invest: true, actions: ['set_dynamic_loss'] },
        ],
      },
      stop_loss: {
        stages: [{ ratio: -0.2, close_invest: true }],
      },
      protect_loss: { ratio: 0, close_invest: true },
      dynamic_loss: { ratio: -0.1, close_invest: true },
    })).toEqual([
      '最长持有：30 个交易日',
      '止盈：当盈利 15% 卖出 30% 触发保护止损；当盈利 25% 清仓 触发动态止损',
      '止损：当亏损 20% 清仓',
      '保护止损：当价格回落到买入成本 清仓',
      '动态止损：当价格从最高回撤 10% 清仓',
    ]);
  });

  it('uses custom description and cost-percent protect / partial dynamic exit', () => {
    expect(formatGoalSummaryLines({
      expiration: { fixed_window_in_days: 20, mode: 'open_day' },
      take_profit: {
        stages: [{
          custom: 'bb_middle',
          description: '日内最高价触及布林中轨',
          exit_ratio: 0,
          actions: ['set_protect_loss'],
        }],
      },
      stop_loss: {
        stages: [{
          custom: 'atr_stop',
          description: 'ATR 通道下破',
          close_invest: true,
        }],
      },
      protect_loss: { ratio: 0.02, close_invest: true },
      dynamic_loss: { ratio: -0.08, exit_ratio: 0.5 },
    })).toEqual([
      '最长持有：20 个开盘日',
      '止盈：（自定义）日内最高价触及布林中轨 触发保护止损',
      '止损：（自定义）ATR 通道下破',
      '保护止损：当价格回落到买入成本的 102% 清仓',
      '动态止损：当价格从最高回撤 8% 卖出 50%',
    ]);
  });

  it('returns an empty list when goal has no stages', () => {
    expect(formatGoalSummaryLines({})).toEqual([]);
  });
});
