import {
  getStrategyCategoryQueryValue,
  getStrategyListPath,
  groupStrategiesByCategory,
  listPeerStrategies,
  readStrategyListCategoryQuery,
  UNKNOWN_STRATEGY_CATEGORY,
  UNKNOWN_STRATEGY_CATEGORY_QUERY,
} from './strategyCategory';

describe('strategyCategory', () => {
  it('maps empty category to unknown query sentinel, not the display label', () => {
    expect(getStrategyCategoryQueryValue({ category: '' })).toBe(UNKNOWN_STRATEGY_CATEGORY_QUERY);
    expect(getStrategyCategoryQueryValue(UNKNOWN_STRATEGY_CATEGORY)).toBe(
      UNKNOWN_STRATEGY_CATEGORY_QUERY,
    );
    expect(getStrategyCategoryQueryValue({ category: '动量' })).toBe('动量');
  });

  it('builds list URLs with encoded category query', () => {
    expect(getStrategyListPath()).toBe('/strategy-design');
    expect(getStrategyListPath('/strategy-design', { category: '动量' })).toBe(
      '/strategy-design?category=%E5%8A%A8%E9%87%8F',
    );
    expect(getStrategyListPath('/strategy-design', { category: { category: '' } })).toBe(
      `/strategy-design?category=${UNKNOWN_STRATEGY_CATEGORY_QUERY}`,
    );
  });

  it('reads category from search string', () => {
    expect(readStrategyListCategoryQuery('?category=__unknown__')).toBe('__unknown__');
    expect(readStrategyListCategoryQuery(new URLSearchParams('category=动量'))).toBe('动量');
    expect(readStrategyListCategoryQuery('')).toBe('');
  });

  it('groups unknown last and attaches queryValue', () => {
    const grouped = groupStrategiesByCategory([
      { name: 'b', category: '震荡' },
      { name: 'a', category: '' },
      { name: 'c', category: '动量' },
    ]);
    expect(grouped.map((g) => g.category)).toEqual(['动量', '震荡', UNKNOWN_STRATEGY_CATEGORY]);
    expect(grouped[2].queryValue).toBe(UNKNOWN_STRATEGY_CATEGORY_QUERY);
  });

  it('sorts rows within a category by display_name naturally', () => {
    const grouped = groupStrategiesByCategory([
      { name: 'low_price', display_name: '演示4b - 低价股（含退市）', category: '演示 · 横截面' },
      { name: 'chase_heat', display_name: '演示2 - 追近月强势', category: '演示 · 横截面' },
      { name: 'low_price_survivor', display_name: '演示4a - 低价股（仅幸存者）', category: '演示 · 横截面' },
    ]);
    expect(grouped).toHaveLength(1);
    expect(grouped[0].rows.map((r) => r.name)).toEqual([
      'chase_heat',
      'low_price_survivor',
      'low_price',
    ]);
  });

  it('lists named-category peers, caps at 5, and skips unknown category', () => {
    const rows = [
      { name: 'a', display_name: '演示7', category: '动量' },
      { name: 'b', key: 'b', display_name: '演示2', category: '动量' },
      { name: 'c', display_name: '演示3', category: '动量' },
      { name: 'd', display_name: '演示4', category: '动量' },
      { name: 'e', display_name: '演示5', category: '动量' },
      { name: 'f', display_name: '演示6', category: '动量' },
      { name: 'g', display_name: '演示8', category: '动量' },
      { name: 'u', category: '' },
    ];
    const listed = listPeerStrategies(rows, { name: 'a' });
    expect(listed.queryValue).toBe('动量');
    expect(listed.totalPeers).toBe(6);
    expect(listed.hasMore).toBe(true);
    expect(listed.peers.map((r) => r.name)).toEqual(['b', 'c', 'd', 'e', 'f']);
    expect(listPeerStrategies(rows, { name: 'u' }).peers).toEqual([]);
    expect(listPeerStrategies(rows, { name: 'missing' }).peers).toEqual([]);
  });
});
