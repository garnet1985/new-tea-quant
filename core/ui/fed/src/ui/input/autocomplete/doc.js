const doc = {
  summary: '自动完成：输入框内过滤并从建议中选择（可多选）。onChange 为 e.target.value。与 SearchSelect / TextField 分立，勿合并。',
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
      description: '建议项。',
    },
    {
      name: 'value / onChange',
      type: '受控',
      defaultValue: '—',
      description: '单选为 option.value；multiple 时为 value 数组。',
    },
    {
      name: 'multiple',
      type: 'boolean',
      defaultValue: 'false',
      description: '多选（芯片）。',
    },
    {
      name: 'placeholder',
      type: 'string',
      defaultValue: "'输入或选择'",
      description: '输入占位。',
    },
    {
      name: 'clearable',
      type: 'boolean',
      defaultValue: 'true',
      description: '是否可清除。',
    },
    {
      name: 'maxWidth',
      type: 'boolean',
      defaultValue: 'true',
      description: '默认约 320px；false 去掉。',
    },
  ],
  scenarios: [
    '可打字筛选的建议列表：执行单元、标签、依赖项。',
    '多选：depends_on 一类字段。',
  ],
  antiPatterns: [
    '封闭枚举用 Select；选项很多但只需点选用 SearchSelect。',
    '仅工具栏关键字过滤用 SearchField。',
  ],
};

export default doc;
