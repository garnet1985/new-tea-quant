import { strategyFeeFields } from './strategyFees';

const strategyPriceSimulatorSchema = {
  name: 'strategyPriceSimulator',
  type: 'fieldGroup',
  label: '',
  children: [
    {
      name: 'priceSimulator.dateRange',
      label: '回测时间段',
      tooltip: '不填写开始或结束日期时，表示使用默认的全部时间区间。',
      type: 'dateRange',
      startName: 'start_date',
      endName: 'end_date',
      startLabel: '开始日期',
      endLabel: '结束日期',
    },
    {
      name: 'use_sampling',
      type: 'switch',
      label: '是否使用采样',
    },
    {
      name: 'priceSimulator.feesOverride',
      type: 'feesOverride',
      label: '费用设置',
      switchLabel: '覆盖全局费用',
      flagName: 'override_fees',
      feesName: 'fees',
      feeFields: strategyFeeFields,
    },
  ],
};

export default strategyPriceSimulatorSchema;
