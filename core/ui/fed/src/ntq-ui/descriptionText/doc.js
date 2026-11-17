const doc = {
  summary: '多行说明文案。按策略描述规则拆行；可用 maxLines 截断。着色交给 className（如 ntq-muted）。',
  params: [
    {
      name: 'text',
      type: 'string | number',
      defaultValue: "''",
      description: '原始说明；空时显示 empty。',
    },
    {
      name: 'className',
      type: 'string',
      defaultValue: "''",
      description: '根节点 class；控色 / 字号。',
    },
    {
      name: 'empty',
      type: 'ReactNode',
      defaultValue: "'—'",
      description: '无内容占位；传 null/\'\' 则不渲染。',
    },
    {
      name: 'maxLines',
      type: 'number | null',
      defaultValue: 'null',
      description: '行数截断（CSS --ntq-description-lines）。',
    },
    {
      name: 'component',
      type: 'elementType',
      defaultValue: "'div'",
      description: '根元素类型。',
    },
  ],
  scenarios: [
    '策略 / Tag / 数据源列表的描述列。',
    '卡片副文案需要多行或截断时。',
  ],
  antiPatterns: [
    '不要在业务里手写 splitStrategyDescription + 多行 <p>。',
    '不要用本组件做富文本 / Markdown。',
  ],
};

export default doc;
