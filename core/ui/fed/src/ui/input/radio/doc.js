const doc = {
  summary: '单选组。plain=圆点；button=扫描页式大按钮卡片（options 可带 description）。direction 为 column / row（button 默认 row）。',
  params: [
    {
      name: 'variant',
      type: "'plain' | 'button'",
      defaultValue: "'plain'",
      description: '圆点 / 大按钮卡片。',
    },
    {
      name: 'label / labelPlacement / tip / hint / error',
      type: '同 Field',
      defaultValue: '—',
      description: '字段壳。',
    },
    {
      name: 'options',
      type: '{ value, label, description?, disabled? }[]',
      defaultValue: '[]',
      description: '选项；button 形态可用 description。',
    },
    {
      name: 'value / onChange / name',
      type: '受控',
      defaultValue: '—',
      description: '当前值与变更。',
    },
    {
      name: 'direction',
      type: "'column' | 'row'",
      defaultValue: "plain→column；button→row",
      description: '排列方向。',
    },
    {
      name: 'disabled',
      type: 'boolean',
      defaultValue: 'false',
      description: '整组禁用。',
    },
  ],
  scenarios: [
    '表单单选：variant 默认 plain。',
    '扫描模式等大选项：variant="button" + description。',
  ],
  antiPatterns: [
    '多选请用 Checkbox。',
    '超长列表优先 Select（v2），不要堆几十个 button。',
  ],
};

export default doc;
