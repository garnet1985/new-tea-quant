const doc = {
  summary: '可搜索下拉：触发器显示当前选中；展开后面板顶部有搜索框，用于过滤长列表。onChange 为 e.target.value。',
  params: [
    {
      name: 'label / labelPlacement / tip / hint / error',
      type: '同 Field',
      defaultValue: '—',
      description: '字段壳。',
    },
    {
      name: 'options',
      type: '{ value, label, disabled? }[]',
      defaultValue: '[]',
      description: '选项；按 label / value 过滤。',
    },
    {
      name: 'value / onChange',
      type: '受控',
      defaultValue: '—',
      description: '当前 option.value；onChange(e) 与 Select 一致。',
    },
    {
      name: 'placeholder',
      type: 'string',
      defaultValue: "'搜索…'",
      description: '面板内搜索框占位（左侧有 search 图标）。',
    },
    {
      name: 'maxWidth',
      type: 'boolean',
      defaultValue: 'true',
      description: '默认约 320px 上限；false 去掉。',
    },
    {
      name: 'emptyLabel',
      type: 'string',
      defaultValue: "'请选择'",
      description: '未选时触发器文案。',
    },
    {
      name: 'clearable',
      type: 'boolean',
      defaultValue: 'true',
      description: '触发器是否可清除。',
    },
    {
      name: 'noOptionsText',
      type: 'string',
      defaultValue: "'无匹配项'",
      description: '无过滤结果时文案。',
    },
  ],
  scenarios: [
    '选项很多：策略、股票池、执行单元 — 展开后搜索过滤。',
  ],
  antiPatterns: [
    '少量固定枚举用 Select。',
    '自由输入建议列表用 Autocomplete；工具栏关键字用 SearchField。',
  ],
};

export default doc;
