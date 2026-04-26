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
  ],
};

export default strategyPriceSimulatorSchema;
