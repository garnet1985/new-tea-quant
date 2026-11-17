const doc = {
  summary: '搜索输入：前缀 search 图标，默认无字段标签（工具栏过滤）。独立于 TextField，勿合并。',
  params: [
    {
      name: 'value / onChange',
      type: '受控',
      defaultValue: '—',
      description: '与 TextField 一致：e.target.value。',
    },
    {
      name: 'placeholder',
      type: 'string',
      defaultValue: "'搜索'",
      description: '占位文案。',
    },
    {
      name: 'label / labelPlacement',
      type: '同 Field',
      defaultValue: "labelPlacement='none'",
      description: '默认无标签；需要表单标签时可 above/inline。',
    },
    {
      name: 'clearable',
      type: 'boolean',
      defaultValue: 'true',
      description: '有内容时显示清除。',
    },
    {
      name: 'maxWidth',
      type: 'boolean',
      defaultValue: 'true',
      description: '默认约 360px；false 去掉。',
    },
    {
      name: 'fluid',
      type: 'boolean',
      defaultValue: 'false',
      description: '工具栏弹性宽（约 200–420px）。',
    },
  ],
  scenarios: [
    '列表页 / 扫描页工具栏按名称过滤。',
  ],
  antiPatterns: [
    '普通表单短文本用 TextField。',
    '封闭选项下拉用 Select / SearchSelect；可打字建议用 Autocomplete。',
  ],
};

export default doc;
