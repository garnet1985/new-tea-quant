import { strategyFeeFields } from './strategyFees';

const strategyPriceSimulatorSchema = {
  name: 'strategyPriceSimulator',
  type: 'fieldGroup',
  label: '',
  children: [
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
