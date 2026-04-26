import { strategyFeeFields } from './strategyFees';

function parseNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  return Number.isNaN(n) ? '' : n;
}

function parseIntNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  if (Number.isNaN(n)) return '';
  return Math.trunc(n);
}

const strategyCapitalSimulatorSchema = {
  name: 'strategyCapitalSimulator',
  type: 'fieldGroup',
  label: '',
  children: [
    {
      name: 'use_sampling',
      type: 'switch',
      label: '是否使用采样',
    },
    {
      name: 'initial_capital',
      type: 'number',
      label: '初始资金',
      parse: parseNumber,
    },
    {
      name: 'allocation.max_portfolio_size',
      type: 'number',
      label: '最大同时持股数',
      description: '同时最多能持有多少只股票（默认 10）',
      parse: parseIntNumber,
    },
    {
      name: 'allocation.mode',
      type: 'select',
      label: '资金分配策略',
      options: [
        { label: '每个机会均等资金买入', value: 'equal_capital' },
        { label: '每个机会均等股数买入', value: 'equal_shares' },
        { label: '凯莉公式', value: 'kelly' },
        { label: '自定义', value: 'custom' },
      ],
    },
    {
      name: 'allocation.max_weight_per_stock',
      type: 'number',
      label: '单票最大权重',
      description: '单只股票最大仓位占比（0~1，默认 0.3）',
      parse: parseNumber,
    },
    {
      name: 'allocation.lot_size',
      type: 'number',
      label: '每手股数',
      description: '仅在“每个机会均等股数买入”模式下生效（默认 100）',
      parse: parseIntNumber,
      visibleWhen: ({ values }) => values?.allocation?.mode === 'equal_shares',
    },
    {
      name: 'allocation.lots_per_trade',
      type: 'number',
      label: '每次买入手数',
      description: '仅在“每个机会均等股数买入”模式下生效（默认 1）',
      parse: parseIntNumber,
      visibleWhen: ({ values }) => values?.allocation?.mode === 'equal_shares',
    },
    {
      name: 'allocation.kelly_fraction',
      type: 'number',
      label: '凯莉折扣系数',
      description: '仅在“凯莉公式”模式下生效（0~1，默认 0.5）',
      parse: parseNumber,
      visibleWhen: ({ values }) => values?.allocation?.mode === 'kelly',
    },
    {
      name: 'capitalSimulator.feesOverride',
      type: 'feesOverride',
      label: '费用设置',
      switchLabel: '覆盖全局费用',
      flagName: 'override_fees',
      feesName: 'fees',
      feeFields: strategyFeeFields,
    },
  ],
};

export default strategyCapitalSimulatorSchema;
