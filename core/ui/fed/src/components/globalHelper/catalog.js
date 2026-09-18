const WORKBENCH_STEPS = new Set(['enum', 'price', 'portfolio']);

export function matchStrategyDesignWorkbench(pathname) {
  const segs = String(pathname || '').split('/').filter(Boolean);
  if (segs[0] !== 'strategy-design' || segs.length < 3) return false;
  const step = decodeURIComponent(segs[segs.length - 1] || '');
  return WORKBENCH_STEPS.has(step);
}

/** 制定策略内页（枚举 / 价格 / 投资组合）三栏简介。 */
export const STRATEGY_DESIGN_HELP = {
  id: 'strategy-design',
  version: 1,
  legacyIds: [],
  match: matchStrategyDesignWorkbench,
  steps: [
    {
      target: 'design-settings',
      pages: [
        {
          title: '设置栏',
          body: '左边这一栏是当前策略的设置。目标、采样、费率和模拟参数都在这里改，会作用在这次回测上。',
        },
        {
          title: '先改再跑',
          body: '不同步骤看到的设置项不一样。改完不用另存，点右侧模拟就会用当前这些值。',
        },
      ],
    },
    {
      target: 'design-execution',
      pages: [
        {
          title: '执行栏',
          body: '这里启动当前这一步的回测，看进度，并进入下一步。',
        },
      ],
    },
    {
      target: 'design-report',
      pages: [
        {
          title: '报告栏',
          body: '回测结果出现在这里。还没跑时是空的，跑完就能看分布、收益和明细。',
        },
      ],
    },
  ],
};

export const GLOBAL_HELPER_CATALOG = [STRATEGY_DESIGN_HELP];

export function findHelpForPath(pathname) {
  return GLOBAL_HELPER_CATALOG.find((help) => help.match(pathname)) || null;
}

export function isHelpDismissed(help, dismissed = {}) {
  if (!help) return false;
  const catalogVersion = Number(help.version) > 0 ? Number(help.version) : 1;
  const ids = [help.id, ...(Array.isArray(help.legacyIds) ? help.legacyIds : [])];
  return ids.some((id) => {
    const row = dismissed[id];
    if (!row) return false;
    return Number(row.version || 0) >= catalogVersion;
  });
}
