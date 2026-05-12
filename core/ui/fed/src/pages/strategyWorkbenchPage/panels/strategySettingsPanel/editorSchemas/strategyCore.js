const strategyCoreSchema = {
  name: 'strategyCore',
  label: '策略核心设置',
  description: '用户自定义策略核心参数',
  type: 'section',
  defaultExpanded: false,
  children: [
    {
      name: 'strategyCore.dictParser',
      label: '核心参数 Dict 编辑器',
      description: '支持 JSON / Python dict 风格输入',
      type: 'dictParser',
      sourceKey: 'coreEditor',
      placeholder: '输入 settings.core（dict）',
    },
  ],
};

export default strategyCoreSchema;
