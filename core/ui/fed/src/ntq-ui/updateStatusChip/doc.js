const doc = {
  summary: '数据更新状态芯片：把 up_to_date / needs_update / needs_recompute 等映射到 Tag；pending 时显示 Loading。',
  params: [
    {
      name: 'status',
      type: 'string',
      defaultValue: "''",
      description: "'up_to_date' | 'needs_update' | 'needs_recompute' | 其它（neutral）。",
    },
    {
      name: 'label',
      type: 'string',
      defaultValue: "'—'",
      description: '展示文案（由业务 / API 提供本地化文案）。',
    },
    {
      name: 'hint',
      type: 'string',
      defaultValue: "''",
      description: '非最新态时旁挂 HelpTooltip；up_to_date 忽略。',
    },
    {
      name: 'pending',
      type: 'boolean',
      defaultValue: 'false',
      description: '状态仍在计算 → inlineRow Loading。',
    },
  ],
  scenarios: [
    '数据源 / Tag / 序列关系列表的「是否最新」列。',
  ],
  antiPatterns: [
    '不要在业务页手写 Tag status 映射规则。',
    '不要把本组件当通用 Tag 用。',
  ],
};

export default doc;
