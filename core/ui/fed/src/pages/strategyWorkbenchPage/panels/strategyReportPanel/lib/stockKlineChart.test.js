import { buildStockKlineChartOptionFromPayload } from './stockKlineChart';

function payload(overrides = {}) {
  return {
    candles: [
      { date: '20240103', open: 10, close: 11, low: 9.5, high: 11.2 },
      { date: '20240104', open: 11, close: 10.5, low: 10.2, high: 11.4 },
      { date: '20240105', open: 10.5, close: 12, low: 10.4, high: 12.1 },
    ],
    markers: [
      { type: 'buy', date: '20240103', label: '买入', detail: { entry_price: 10.1 } },
      { type: 'target_win', date: '20240105', label: '目标胜', detail: { roi: 0.1 } },
    ],
    ...overrides,
  };
}

describe('stockKlineChart', () => {
  it('uses scatter markers with data instead of empty legend series or candlestick markPoint', () => {
    const option = buildStockKlineChartOptionFromPayload(payload());
    const kline = option.series.find((s) => s.name === 'K线');
    expect(kline.type).toBe('candlestick');
    expect(kline.markPoint).toBeUndefined();

    const buy = option.series.find((s) => s.name === '买入');
    const win = option.series.find((s) => s.name === '目标胜');
    expect(buy.type).toBe('scatter');
    expect(buy.data.length).toBe(1);
    expect(buy.data[0].value).toEqual(['20240103', 9.5]);
    expect(win.data[0].value).toEqual(['20240105', 12.1]);
    expect(option.series.every((s) => !Array.isArray(s.data) || s.data.length > 0)).toBe(true);
    expect(option.dataZoom[0].filterMode).toBe('none');
  });

  it('puts marker detail into the axis tooltip', () => {
    const option = buildStockKlineChartOptionFromPayload(payload());
    const html = option.tooltip.formatter([
      {
        seriesType: 'candlestick',
        axisValue: '20240103',
        dataIndex: 0,
      },
      {
        seriesType: 'scatter',
        seriesName: '买入',
        axisValue: '20240103',
        data: {
          value: ['20240103', 9.5],
          _markerMeta: { type: 'buy', date: '20240103', label: '买入', detail: { entry_price: 10.1 } },
        },
      },
    ]);
    expect(html).toContain('买入');
    expect(html).toContain('入场价');
    expect(html).toContain('开盘');
  });

  it('keeps a scatter point for each staged exit', () => {
    const option = buildStockKlineChartOptionFromPayload(
      payload({
        markers: [
          { type: 'buy', date: '20240103', label: '买入', detail: { entry_price: 10.1 } },
          {
            type: 'target_win',
            date: '20240104',
            label: '目标胜',
            detail: { goal_name: 'win20%', exit_ratio: 0.5, roi: 0.05 },
          },
          {
            type: 'target_win',
            date: '20240105',
            label: '目标胜',
            detail: { goal_name: 'win30%', exit_ratio: 0.5, roi: 0.1 },
          },
        ],
      })
    );
    const win = option.series.find((s) => s.name === '目标胜');
    expect(win.data.map((d) => d.value[0])).toEqual(['20240104', '20240105']);
    const html = option.tooltip.formatter([
      {
        seriesType: 'scatter',
        seriesName: '目标胜',
        axisValue: '20240104',
        data: {
          value: ['20240104', 11.4],
          _markerMeta: {
            type: 'target_win',
            date: '20240104',
            label: '目标胜',
            detail: { goal_name: 'win20%', exit_ratio: 0.5 },
          },
        },
      },
    ]);
    expect(html).toContain('win20%');
    expect(html).toContain('50%');
  });

  it('collapses same-day staged exits into one pin', () => {
    const option = buildStockKlineChartOptionFromPayload(
      payload({
        markers: [
          { type: 'buy', date: '20240103', label: '买入', detail: { entry_price: 10.1 } },
          {
            type: 'target_win',
            date: '20240105',
            label: '目标胜',
            detail: { goal_name: 'win20%', exit_ratio: 0.5, roi: 0.05 },
          },
          {
            type: 'target_win',
            date: '20240105',
            label: '目标胜',
            detail: { goal_name: 'win30%', exit_ratio: 0.5, roi: 0.1 },
          },
        ],
      })
    );
    const win = option.series.find((s) => s.name === '目标胜');
    expect(win.data).toHaveLength(1);
    expect(win.data[0].value).toEqual(['20240105', 12.1]);
    expect(win.data[0]._markerMeta.detail.goal_name).toBe('win20%、win30%');
    expect(win.data[0]._markerMeta.detail.exit_ratio).toBe(1);
  });
});
