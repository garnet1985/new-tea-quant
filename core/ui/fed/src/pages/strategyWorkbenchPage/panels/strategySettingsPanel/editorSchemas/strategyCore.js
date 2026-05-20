const strategyCoreSchema = {
  name: 'strategyCore',
  label: '策略核心设置',
  type: 'section',
  defaultExpanded: false,
  children: [
    {
      name: 'strategyCore.dictParser',
      label: '核心参数',
      tooltip: '在策略代码里的一些自定义阈值或者参数，来源于策略设置文件里的core参数块',
      type: 'dictParser',
      sourceKey: 'coreEditor',
      placeholder: '输入 settings.core（dict）',
    },
  ],
};

export default strategyCoreSchema;
