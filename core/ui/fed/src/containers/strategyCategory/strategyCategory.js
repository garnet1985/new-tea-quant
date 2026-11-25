/** 无 ``meta.category`` 时的 UI 归类名。 */
export const UNKNOWN_STRATEGY_CATEGORY = '未知归类';

/** URL query 哨兵：``?category=__unknown__`` 表示无归类，不使用展示文案。 */
export const UNKNOWN_STRATEGY_CATEGORY_QUERY = '__unknown__';

export const STRATEGY_LIST_CATEGORY_PARAM = 'category';

/** 策略归类展示名：有 category 用原文，否则「未知归类」。 */
export function getStrategyCategoryLabel(itemOrCategory) {
  if (itemOrCategory && typeof itemOrCategory === 'object') {
    const category = String(itemOrCategory.category || '').trim();
    return category || UNKNOWN_STRATEGY_CATEGORY;
  }
  const label = String(itemOrCategory || '').trim();
  return label || UNKNOWN_STRATEGY_CATEGORY;
}

/**
 * 列表 URL 用的 category 值。空归类 → ``__unknown__``；命名类用原文。
 * @param {object|string|null|undefined} itemOrCategory 目录行，或展示名 / query 值
 */
export function getStrategyCategoryQueryValue(itemOrCategory) {
  if (itemOrCategory && typeof itemOrCategory === 'object') {
    const raw = String(itemOrCategory.category || '').trim();
    return raw || UNKNOWN_STRATEGY_CATEGORY_QUERY;
  }
  const raw = String(itemOrCategory || '').trim();
  if (!raw || raw === UNKNOWN_STRATEGY_CATEGORY || raw === UNKNOWN_STRATEGY_CATEGORY_QUERY) {
    return UNKNOWN_STRATEGY_CATEGORY_QUERY;
  }
  return raw;
}

export function readStrategyListCategoryQuery(search) {
  const params = new URLSearchParams(
    search instanceof URLSearchParams ? search : String(search || ''),
  );
  return String(params.get(STRATEGY_LIST_CATEGORY_PARAM) || '').trim();
}

/**
 * 策略选择页路径。``category`` 可进行目录行或展示名；``categoryQuery`` 已是 query 值。
 * @param {string} [listBasePath]
 * @param {{ category?: object|string, categoryQuery?: string }} [options]
 */
export function getStrategyListPath(listBasePath = '/strategy-design', options = {}) {
  const base = String(listBasePath || '/strategy-design').replace(/[?#].*$/, '') || '/strategy-design';
  let queryValue = String(options.categoryQuery ?? '').trim();
  if (!queryValue && options.category != null && options.category !== '') {
    queryValue = getStrategyCategoryQueryValue(options.category);
  }
  if (!queryValue) return base;
  const params = new URLSearchParams();
  params.set(STRATEGY_LIST_CATEGORY_PARAM, queryValue);
  return `${base}?${params.toString()}`;
}

export const STRATEGY_PEER_LIST_LIMIT = 5;

/** 列表展示名：prefer display_name，再回退 name / key。 */
export function getStrategySortLabel(row) {
  return String(
    row?.display_name || row?.displayName || row?.name || row?.key || '',
  ).trim();
}

/** 同类内排序：按展示名自然序（演示1/2/4a/4b…），同名再比 path。 */
export function compareStrategiesForList(a, b) {
  const byLabel = getStrategySortLabel(a).localeCompare(
    getStrategySortLabel(b),
    'zh-CN',
    { numeric: true, sensitivity: 'base' },
  );
  if (byLabel !== 0) return byLabel;
  return String(a?.path || a?.name || '').localeCompare(
    String(b?.path || b?.name || ''),
    'zh-CN',
    { numeric: true },
  );
}

function strategyRowIds(row) {
  return [
    String(row?.name || '').trim(),
    String(row?.key || '').trim(),
    String(row?.path || '').trim(),
  ].filter(Boolean);
}

export function isSameStrategyRow(row, current = {}) {
  const currentIds = new Set(
    [current.name, current.key, current.path]
      .map((v) => String(v || '').trim())
      .filter(Boolean),
  );
  if (currentIds.size === 0) return false;
  return strategyRowIds(row).some((id) => currentIds.has(id));
}

/**
 * 当前策略的同归类邻居（不含自己）。无命名归类或没有邻居时 peers 为空。
 * @returns {{ categoryLabel: string, queryValue: string, peers: object[], totalPeers: number, hasMore: boolean }}
 */
export function listPeerStrategies(rows, current, { limit = STRATEGY_PEER_LIST_LIMIT } = {}) {
  const list = Array.isArray(rows) ? rows : [];
  const currentRow = list.find((row) => isSameStrategyRow(row, current));
  const empty = {
    categoryLabel: '',
    queryValue: '',
    peers: [],
    totalPeers: 0,
    hasMore: false,
  };
  if (!currentRow) return empty;
  const queryValue = getStrategyCategoryQueryValue(currentRow);
  if (queryValue === UNKNOWN_STRATEGY_CATEGORY_QUERY) {
    return { ...empty, categoryLabel: UNKNOWN_STRATEGY_CATEGORY, queryValue };
  }
  const peers = list
    .filter((row) => (
      getStrategyCategoryQueryValue(row) === queryValue
      && !isSameStrategyRow(row, current)
    ))
    .slice()
    .sort(compareStrategiesForList);
  const cap = Math.max(0, Number(limit) || 0);
  return {
    categoryLabel: getStrategyCategoryLabel(currentRow),
    queryValue,
    peers: peers.slice(0, cap),
    totalPeers: peers.length,
    hasMore: peers.length > cap,
  };
}

/**
 * 按 category 分组；命名类按中文序，``未知归类`` 始终在最后。
 * 组内按展示名自然序（便于演示1/2/4a/4b 按编号排列）。
 * @param {object[]} rows
 * @returns {{ category: string, queryValue: string, rows: object[] }[]}
 */
export function groupStrategiesByCategory(rows) {
  const map = new Map();
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const category = getStrategyCategoryLabel(row);
    if (!map.has(category)) map.set(category, []);
    map.get(category).push(row);
  });
  const named = [...map.keys()]
    .filter((name) => name !== UNKNOWN_STRATEGY_CATEGORY)
    .sort((a, b) => a.localeCompare(b, 'zh-CN'));
  const order = [...named];
  if (map.has(UNKNOWN_STRATEGY_CATEGORY)) {
    order.push(UNKNOWN_STRATEGY_CATEGORY);
  }
  return order.map((category) => ({
    category,
    queryValue: getStrategyCategoryQueryValue(category),
    rows: (map.get(category) || []).slice().sort(compareStrategiesForList),
  }));
}
