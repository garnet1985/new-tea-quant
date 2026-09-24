import {
  buildPortfolioTradeLifecycleChartOption,
  buildTradeLifecycleTableRows,
  formatHoldingPeriodLabel,
  holdingCalendarDays,
  pairTradeLifecycles,
} from './portfolioTradeLifecycle';

describe('pairTradeLifecycles', () => {
  it('pairs by investmentId across partial sells', () => {
    const lives = pairTradeLifecycles([
      {
        date: '20240103',
        side: 'buy',
        investmentId: '1',
        entityId: '000001.SZ',
        stockName: '平安银行',
        shares: 200,
        price: 10,
      },
      {
        date: '20240110',
        side: 'sell',
        investmentId: '1',
        entityId: '000001.SZ',
        shares: 100,
        price: 11,
        profit: 100,
      },
      {
        date: '20240117',
        side: 'sell',
        investmentId: '1',
        entityId: '000001.SZ',
        shares: 100,
        price: 12,
        profit: 200,
      },
    ]);
    expect(lives).toHaveLength(1);
    expect(lives[0].endDate).toBe('20240117');
    expect(lives[0].profit).toBe(300);
    expect(lives[0].outcome).toBe('profit');
    expect(lives[0].sells).toHaveLength(2);
  });

  it('keeps separate lots when investmentId collides across stocks', () => {
    const lives = pairTradeLifecycles([
      {
        date: '20240103',
        side: 'buy',
        investmentId: '1',
        entityId: 'AAA.SZ',
        stockName: '甲',
        shares: 100,
        price: 10,
        cost: 1000,
      },
      {
        date: '20240103',
        side: 'buy',
        investmentId: '1',
        entityId: 'BBB.SZ',
        stockName: '乙',
        shares: 200,
        price: 20,
        cost: 4000,
      },
      {
        date: '20240110',
        side: 'sell',
        investmentId: '1',
        entityId: 'AAA.SZ',
        shares: 100,
        price: 11,
        profit: 100,
      },
      {
        date: '20240111',
        side: 'sell',
        investmentId: '1',
        entityId: 'BBB.SZ',
        shares: 200,
        price: 18,
        profit: -400,
      },
    ]);
    expect(lives).toHaveLength(2);
    expect(new Set(lives.map((l) => l.id)).size).toBe(2);
    expect(lives[0].entityId).toBe('AAA.SZ');
    expect(lives[0].profit).toBe(100);
    expect(lives[1].entityId).toBe('BBB.SZ');
    expect(lives[1].profit).toBe(-400);
  });

  it('falls back to FIFO when investmentId is missing', () => {
    const lives = pairTradeLifecycles([
      { date: '20240103', side: 'buy', entityId: 'A', shares: 100, price: 10 },
      { date: '20240105', side: 'buy', entityId: 'A', shares: 50, price: 11 },
      { date: '20240110', side: 'sell', entityId: 'A', shares: 100, price: 9, profit: -100 },
      { date: '20240112', side: 'sell', entityId: 'A', shares: 50, price: 12, profit: 50 },
    ]);
    expect(lives).toHaveLength(2);
    expect(lives[0].outcome).toBe('loss');
    expect(lives[0].endDate).toBe('20240110');
    expect(lives[1].outcome).toBe('profit');
    expect(lives[1].endDate).toBe('20240112');
  });

  it('keeps open buys without an end', () => {
    const lives = pairTradeLifecycles([
      { date: '20240103', side: 'buy', investmentId: '9', entityId: 'B', shares: 10, price: 1 },
    ]);
    expect(lives[0].outcome).toBe('open');
    expect(lives[0].endDate).toBeNull();
  });
});

describe('buildPortfolioTradeLifecycleChartOption', () => {
  const metrics = {
    marketProfile: 'china_a_stock',
    eventCurveLabels: ['20240103', '20240110', '20240117'],
    eventCurveValues: [1000000, 980000, 1100000],
    tradeEvents: [
      {
        date: '20240103',
        side: 'buy',
        investmentId: '1',
        entityId: '000001.SZ',
        stockName: '平安银行',
        shares: 100,
        price: 10.5,
      },
      {
        date: '20240110',
        side: 'sell',
        investmentId: '1',
        entityId: '000001.SZ',
        stockName: '平安银行',
        shares: 40,
        price: 11,
        profit: 20,
      },
      {
        date: '20240117',
        side: 'sell',
        investmentId: '1',
        entityId: '000001.SZ',
        stockName: '平安银行',
        shares: 60,
        price: 12,
        profit: 90,
      },
    ],
  };

  it('paints equity curve with start dots only by default', () => {
    const option = buildPortfolioTradeLifecycleChartOption(metrics);
    expect(option.xAxis.data).toEqual(['20240103', '20240110', '20240117']);
    expect(option.series.map((s) => s.name)).toEqual(['总资产', '持有指引', '开仓', '事件']);
    const equity = option.series.find((s) => s.name === '总资产');
    expect(equity.type).toBe('line');
    expect(equity.data).toEqual([1000000, 980000, 1100000]);
    const starts = option.series.find((s) => s.name === '开仓');
    const events = option.series.find((s) => s.name === '事件');
    expect(starts.data).toHaveLength(1);
    expect(starts.data[0].symbol).toBe('circle');
    expect(starts.data[0].value[1]).toBe(1000000);
    expect(events.data).toHaveLength(0);
    expect(option.series.find((s) => s.name === '持有指引').markLine.data).toEqual([]);
  });

  it('on hover shows all sell events of that investment on the curve', () => {
    const base = buildPortfolioTradeLifecycleChartOption(metrics);
    const lifeId = base.series.find((s) => s.name === '开仓').data[0].lifecycle.id;
    const option = buildPortfolioTradeLifecycleChartOption(metrics, {
      activeLifecycleId: lifeId,
    });
    const events = option.series.find((s) => s.name === '事件');
    expect(events.data).toHaveLength(2);
    expect(events.data.map((d) => d.value[0])).toEqual(['20240110', '20240117']);
    const activeStart = option.series.find((s) => s.name === '开仓').data[0];
    expect(activeStart.symbol).toContain('path://');
    const guide = option.series.find((s) => s.name === '持有指引');
    expect(guide.markLine.data).toHaveLength(2);
    expect(guide.markArea.data).toHaveLength(1);
    const tip = option.tooltip.formatter({
      seriesName: '事件',
      data: events.data[0],
    });
    expect(tip).toContain('平安银行');
    expect(tip).toContain('卖出');
  });

  it('focus mode windows the curve and always paints that trade events', () => {
    const longMetrics = {
      ...metrics,
      eventCurveLabels: [
        '20231201', '20231215', '20240103', '20240110', '20240117', '20240201', '20240215',
      ],
      eventCurveValues: [1e6, 1e6, 1e6, 9.8e5, 1.1e6, 1.1e6, 1.1e6],
    };
    const lifeId = pairTradeLifecycles(longMetrics.tradeEvents)[0].id;
    const option = buildPortfolioTradeLifecycleChartOption(longMetrics, {
      focusLifecycleId: lifeId,
    });
    expect(option.series.find((s) => s.name === '开仓').data).toHaveLength(1);
    expect(option.series.find((s) => s.name === '事件').data).toHaveLength(2);
    expect(option.xAxis.data[0]).toBe('20231201');
    expect(option.dataZoom[0].type).toBe('slider');
  });
});

describe('holding period labels', () => {
  it('counts inclusive calendar days', () => {
    expect(holdingCalendarDays('20240103', '20240103')).toBe(1);
    expect(holdingCalendarDays('20240103', '20240117')).toBe(15);
  });

  it('formats closed and open holdings', () => {
    expect(formatHoldingPeriodLabel('20240103', '20240117')).toBe(
      '2024-01-03 - 2024-01-17：共15天',
    );
    expect(formatHoldingPeriodLabel('20240103', null, { open: true })).toBe(
      '2024-01-03 - 未平仓',
    );
  });
});

describe('buildTradeLifecycleTableRows', () => {
  it('builds stock / holding / investment / return fields', () => {
    const rows = buildTradeLifecycleTableRows([
      {
        date: '20240103',
        side: 'buy',
        investmentId: '1',
        entityId: '000001.SZ',
        stockName: '平安银行',
        shares: 100,
        price: 10,
        cost: 1000,
      },
      {
        date: '20240117',
        side: 'sell',
        investmentId: '1',
        entityId: '000001.SZ',
        shares: 100,
        price: 12,
        profit: 200,
      },
      {
        date: '20240105',
        side: 'buy',
        investmentId: '2',
        entityId: '000002.SZ',
        stockName: '万科A',
        shares: 50,
        price: 8,
      },
    ]);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      entityId: '000001.SZ',
      stockName: '平安银行',
      startDate: '20240103',
      endDate: '20240117',
      holdingDays: 15,
      holdingLabel: '2024-01-03 - 2024-01-17：共15天',
      shares: 100,
      buyPrice: 10,
      cost: 1000,
      exitPrice: 12,
      returnPct: 20,
      profit: 200,
      open: false,
    });
    expect(rows[1].open).toBe(true);
    expect(rows[1].holdingLabel).toBe('2024-01-05 - 未平仓');
    expect(rows[1].cost).toBe(400);
    expect(rows[1].returnPct).toBeNull();
    expect(rows[1].profit).toBeNull();
  });
});
