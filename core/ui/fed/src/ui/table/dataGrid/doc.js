const doc = {
  summary: 'NTQ 表格：封装 MUI DataGrid，默认中文、Loading 覆盖层、无边框与禁用点击选行；业务列定义仍透传。',
  params: [
    {
      name: 'rows / columns',
      type: 'array',
      defaultValue: '—',
      description: '与 MUI DataGrid 相同：行数据与列定义。',
    },
    {
      name: 'density',
      type: "'sm' | 'md'",
      defaultValue: "'md'",
      description: '行高密度：sm=紧凑（compact），md=标准（standard）。',
    },
    {
      name: 'loading',
      type: 'boolean',
      defaultValue: 'false',
      description: '显示竖条 Loading 覆盖层。',
    },
    {
      name: 'autoHeight',
      type: 'boolean',
      defaultValue: 'false',
      description: '按行数撑开高度；否则需父级给高度或传 style/sx height。',
    },
    {
      name: 'localeText / slots / …',
      type: 'MUI DataGrid props',
      defaultValue: '中文 + Loading slots',
      description: '其余 props 透传；slots 会与默认 loadingOverlay 合并（业务可覆盖）。',
    },
  ],
  scenarios: [
    '列表页：autoHeight + paginationModel。',
    '固定高度面板：父级 height + 不传 autoHeight。',
    '紧凑报表：density="sm"。',
  ],
  antiPatterns: [
    '不要在业务页再手写一套 DataGrid 中文 / Loading（用本组件）。',
    '不要把领域列渲染逻辑写死进 DataGrid（列定义留在页面）。',
    '不要用裸 px 改单元格样式；优先 density 与本组件 class。',
  ],
};

export default doc;
