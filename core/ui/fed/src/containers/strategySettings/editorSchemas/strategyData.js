/** 与 ``settings_example`` 第 3 节 ``data`` 对齐（K 线与指标门槛） */
export const strategyDataSchema = {
  name: 'strategyData',
  type: 'fieldGroup',
  label: '',
  children: [
    {
      name: 'data.min_required_records',
      label: '回测所需最小 K 线数',
      tooltip: '策略回测需要的最小 K 线数量；若不足该数量，该股票会被跳过',
      type: 'number',
    },
  ],
};

export default strategyDataSchema;
