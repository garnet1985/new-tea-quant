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

  it('lists named-category peers, caps at 5, and skips unknown category', () => {
    const rows = [
      { name: 'a', category: '动量' },
      { name: 'b', key: 'b', category: '动量' },
      { name: 'c', category: '动量' },
      { name: 'd', category: '动量' },
      { name: 'e', category: '动量' },
      { name: 'f', category: '动量' },
      { name: 'g', category: '动量' },
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
