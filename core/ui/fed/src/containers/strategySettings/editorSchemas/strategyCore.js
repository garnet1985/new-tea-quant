const strategyCoreSchema = {
  name: 'strategyCore',
  label: '策略核心设置',
  type: 'section',
  defaultExpanded: false,
  children: [
    {
      name: 'strategyCore.dictParser',
      label: '核心参数',
      tooltip: '策略自定义参数，对应 settings.py 中的 core 配置块',
      type: 'dictParser',
      sourceKey: 'coreEditor',
      placeholder: '输入 settings.py 中的 core 参数',
    },
  ],
};

export default strategyCoreSchema;
