import {
  buildPortfolioEventChartOption,
  groupTradeEventsByDate,
} from './portfolioEventChart';

describe('portfolioEventChart', () => {
  it('clusters same-day buys and sells', () => {
    const byDate = groupTradeEventsByDate([
      { date: '20240103', side: 'buy', stockName: '平安银行', shares: 100, price: 10 },
      { date: '20240103', side: 'buy', stockName: '茅台', shares: 200, price: 1600 },
      { date: '20240103', side: 'sell', stockName: '平安银行', shares: 100, price: 11 },
      { date: '20240110', side: 'sell', entityId: '000002.SZ', shares: 50, price: 8 },
    ]);
    expect(byDate.get('20240103').buys).toHaveLength(2);
    expect(byDate.get('20240103').sells).toHaveLength(1);
    expect(byDate.get('20240110').sells).toHaveLength(1);
  });

  it('uses the full event curve and does not paint trade markers', () => {
    const option = buildPortfolioEventChartOption({
      initialCapital: 1000000,
      finalEquity: 1100000,
      equityCurveLabels: ['20240103', '20240117'],
      equityCurveValues: [1000000, 1100000],
      drawdownCurveValues: [0, 0],
      eventCurveLabels: ['20240103', '20240110', '20240117'],
      eventCurveValues: [1000000, 980000, 1100000],
      eventDrawdownValues: [0, 2, 0],
      tradeEvents: [
        { date: '20240103', side: 'buy', stockName: '平安银行', entityId: '000001.SZ', shares: 100, price: 10.5, cost: 1050 },
        { date: '20240117', side: 'sell', stockName: '平安银行', entityId: '000001.SZ', shares: 100, price: 12, profit: 150, buyPrice: 10.5 },
      ],
    });
    expect(option.xAxis[0].data).toEqual(['20240103', '20240110', '20240117']);
    expect(option.grid).toHaveLength(2);
    expect(option.series.map((s) => s.name)).toEqual(['总资产', '回撤']);
    expect(option.legend.data).toEqual(['总资产']);
    expect(option.series.find((s) => s.name === '回撤').xAxisIndex).toBe(1);
    const html = option.tooltip.formatter([
      { seriesName: '总资产', axisValue: '20240103', data: 1000000 },
    ]);
    expect(html).toContain('回撤：0.00%');
    expect(html).toContain('总资产');
    expect(html).not.toContain('买入');
    expect(html).not.toContain('卖出');
    expect(option.grid[0].height).toBe(option.grid[1].height);
    expect(option.dataZoom[0].type).toBe('slider');
    expect(option.toolbox.feature.restore).toBeTruthy();
  });

  it('falls back to the downsampled curve when event series is missing', () => {
    const option = buildPortfolioEventChartOption({
      initialCapital: 1,
      finalEquity: 1,
      equityCurveLabels: ['20240103', '20240117'],
      equityCurveValues: [1, 2],
      drawdownCurveValues: [0, 0],
    });
    expect(option.xAxis[0].data).toEqual(['20240103', '20240117']);
    expect(option.series.map((s) => s.name)).toEqual(['总资产', '回撤']);
    expect(option.legend.data).toEqual(['总资产']);
  });
});
