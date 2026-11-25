const doc = {
  summary: '复选框。label 为右侧选项文案；可选 fieldLabel + tip/hint/error 走 Field。',
  params: [
    {
      name: 'label',
      type: 'ReactNode',
      defaultValue: "''",
      description: '勾选框右侧文案。',
    },
    {
      name: 'fieldLabel',
      type: 'ReactNode',
      defaultValue: "''",
      description: '字段级标签（少用）；配合 labelPlacement。',
    },
    {
      name: 'labelPlacement',
      type: "'above' | 'inline' | 'none'",
      defaultValue: "'none'",
      description: '仅在有 fieldLabel 时有意义。',
    },
    {
      name: 'checked / onChange',
      type: '受控',
      defaultValue: '—',
      description: 'MUI Checkbox 事件。',
    },
    {
      name: 'disabled / tip / hint / error',
      type: '常用',
      defaultValue: '—',
      description: '禁用与说明。',
    },
  ],
  scenarios: [
    '开关式同意、启用项。',
  ],
  antiPatterns: [
    '多选一组请后续用 CheckboxGroup（本版不做）。',
    '单选互斥用 RadioGroup。',
  ],
};

export default doc;
