import { buildMarketChartOption } from './buildMarketChartOption';
import {
  buildMarketChartOptionFromStockPayload,
  stockKlinePayloadToMarketChartModel,
} from './adapters/stockKlinePayload';

describe('buildMarketChartOption', () => {
  it('builds price + volume + oscillator panes', () => {
    const option = buildMarketChartOption({
      categories: ['20240103', '20240104', '20240105'],
      panes: [
        { id: 'price', heightRatio: 0.5, yAxis: { scale: true } },
        { id: 'volume', heightRatio: 0.15, yAxis: { scale: true } },
        { id: 'oscillator', heightRatio: 0.2, yAxis: { min: 0, max: 100 } },
      ],
      series: [
        {
          type: 'candlestick',
          paneId: 'price',
          key: 'kline',
          label: 'K线',
          data: [
            [10, 11, 9.5, 11.2],
            [11, 10.5, 10.2, 11.4],
            [10.5, 12, 10.4, 12.1],
          ],
        },
        {
          type: 'bar',
          paneId: 'volume',
          key: 'volume',
          label: '成交量',
          color: 'candle',
          data: [100, 120, 90],
        },
        {
          type: 'line',
          paneId: 'oscillator',
          key: 'rsi14',
          label: 'RSI(14)',
          data: [40, 55, 70],
        },
      ],
    });

    expect(option.grid).toHaveLength(3);
    expect(option.xAxis).toHaveLength(3);
    expect(option.yAxis[2].min).toBeLessThan(0);
    expect(option.yAxis[2].max).toBeGreaterThan(100);
    expect(option.series.find((s) => s.type === 'candlestick')).toBeTruthy();
    expect(option.series.find((s) => s.name === '成交量').type).toBe('bar');
    expect(option.series.find((s) => s.name === 'RSI(14)').yAxisIndex).toBe(2);
    expect(option.dataZoom[0].xAxisIndex).toEqual([0, 1, 2]);
  });

  it('renders macd histogram as signed bars on a macd pane', () => {
    const option = buildMarketChartOption({
      categories: ['20240103', '20240104'],
      panes: [
        { id: 'price', heightRatio: 0.55 },
        { id: 'macd', heightRatio: 0.25, yAxis: { scale: true } },
      ],
      series: [
        {
          type: 'candlestick',
          paneId: 'price',
          label: 'K线',
          data: [[10, 11, 9, 12], [11, 10, 9.5, 11.5]],
        },
        {
          type: 'line',
          paneId: 'macd',
          key: 'dif',
          label: 'DIF',
          data: [0.1, -0.2],
        },
        {
          type: 'bar',
          paneId: 'macd',
          key: 'hist',
          label: 'MACDh',
          color: 'signed',
          data: [0.05, -0.08],
        },
      ],
    });
    const hist = option.series.find((s) => s.name === 'MACDh');
    expect(hist.type).toBe('bar');
    expect(hist.data[0].itemStyle.color).toBeTruthy();
    expect(hist.data[1].value).toBe(-0.08);
  });
});

describe('stockKlinePayload adapter', () => {
  function payload(overrides = {}) {
    return {
      candles: [
        { date: '20240103', open: 10, close: 11, low: 9.5, high: 11.2, volume: 1000 },
        { date: '20240104', open: 11, close: 10.5, low: 10.2, high: 11.4, volume: 1100 },
        { date: '20240105', open: 10.5, close: 12, low: 10.4, high: 12.1, volume: 900 },
      ],
      markers: [
        { type: 'buy', date: '20240103', label: '买入', detail: { entry_price: 10.1 } },
        { type: 'target_win', date: '20240105', label: '目标胜', detail: { roi: 0.1 } },
      ],
      ...overrides,
    };
  }

  it('maps volume and oscillator into MarketChartModel panes', () => {
    const model = stockKlinePayloadToMarketChartModel(
      payload({
        indicator_series: [
          {
            key: 'sma20',
            label: 'SMA(20)',
            panel: 'overlay',
            data: [10, 10.5, 11],
          },
          {
            key: 'rsi14',
            label: 'RSI(14)',
            panel: 'oscillator',
            data: [40, 50, 60],
          },
          {
            key: 'macdh',
            label: 'MACDh',
            panel: 'macd',
            kind: 'bar',
            pane_group: 'macd:12_26_9',
            color: 'signed',
            data: [0.1, -0.2, 0.05],
          },
        ],
      }),
    );
    expect(model.panes.map((p) => p.id)).toEqual([
      'price',
      'volume',
      'oscillator',
      'macd:12_26_9',
    ]);
    const subHeights = model.panes.filter((p) => p.id !== 'price').map((p) => p.heightRatio);
    expect(subHeights.every((h) => h === subHeights[0])).toBe(true);
    const priceH = model.panes.find((p) => p.id === 'price').heightRatio;
    expect(priceH / subHeights[0]).toBeGreaterThanOrEqual(5);
    expect(model.panes.find((p) => p.id === 'volume').title).toBe('成交量');
    expect(model.panes.find((p) => p.id === 'macd:12_26_9').title).toBe('MACD');
    expect(model.panes.find((p) => p.id === 'oscillator').title).toMatch(/RSI/);
    expect(model.series.some((s) => s.type === 'candlestick')).toBe(true);
    expect(model.series.some((s) => s.key === 'volume')).toBe(true);
    expect(model.series.find((s) => s.key === 'macdh').type).toBe('bar');
  });

  it('applies linked_ohlcv and macro_step chart layers', () => {
    const model = stockKlinePayloadToMarketChartModel(
      payload({
        indicator_series: [],
        chart_layers: [
          {
            role: 'linked_ohlcv',
            data_key: 'stock.kline.weekly',
            label: '周收',
            points: [
              { date: '20240103', close: 10.2 },
              { date: '20240105', close: 11.5 },
            ],
          },
          {
            role: 'macro_step',
            data_key: 'macro.gdp',
            label: 'GDP YoY',
            points: [{ date: '20240101', value: 5.2 }],
          },
          {
            role: 'event_pins',
            data_key: 'stock.finance.quarterly',
            label: '财报',
            events: [
              {
                date: '20240105',
                label: '财报',
                quarter: '2023Q4',
                snapshot: { roe: 12.3 },
              },
            ],
          },
        ],
      }),
    );
    expect(model.series.some((s) => s.key === 'layer:stock.kline.weekly')).toBe(true);
    expect(model.panes.some((p) => String(p.id).startsWith('macro:'))).toBe(true);
    expect(model.markers.some((m) => m.key === 'finance')).toBe(true);
    expect(model.financeEvents).toHaveLength(1);
  });

  it('drops SuperTrend/PSAR auxiliary columns before painting', () => {
    const model = stockKlinePayloadToMarketChartModel(
      payload({
        indicator_series: [
          {
            key: 'supert_10_3.0',
            label: 'SUPERTREND 主轨',
            panel: 'overlay',
            data: [9, 9.5, 10],
          },
          {
            key: 'supertd_10_3.0',
            label: 'SUPERTREND',
            panel: 'overlay',
            data: [1, -1, 1],
          },
          {
            key: 'psarl_0.02_0.2',
            label: 'PSAR 多',
            panel: 'overlay',
            data: [9.2, 9.3, 9.4],
          },
          {
            key: 'psaraf_0.02_0.2',
            label: 'PSARAF',
            panel: 'overlay',
            data: [0.02, 0.04, 0.06],
          },
          {
            key: 'psarr_0.02_0.2',
            label: 'PSARR',
            panel: 'overlay',
            data: [0, 1, 0],
          },
        ],
      }),
    );
    const keys = model.series.map((s) => s.key);
    expect(keys).toContain('supert_10_3.0');
    expect(keys).toContain('psarl_0.02_0.2');
    expect(keys).not.toContain('supertd_10_3.0');
    expect(keys).not.toContain('psaraf_0.02_0.2');
    expect(keys).not.toContain('psarr_0.02_0.2');
  });

  it('draws outer top/bottom borders and one line between panes', () => {
    const option = buildMarketChartOptionFromStockPayload(
      payload({
        indicator_series: [
          {
            key: 'rsi14',
            label: 'RSI(14)',
            panel: 'oscillator',
            data: [40, 50, 60],
          },
        ],
      }),
    );
    const hLines = (option.graphic || []).filter(
      (g) => g.type === 'rect' && g.shape?.height === 1,
    );
    // price 顶 + price底/volume顶 + volume底/osc顶 + osc底 → 4
    expect(hLines.length).toBe(4);
  });

  it('does not cap candlestick width with barMaxWidth', () => {
    const option = buildMarketChartOptionFromStockPayload(payload());
    const kline = option.series.find((s) => s.type === 'candlestick');
    expect(kline.barMaxWidth).toBeUndefined();
    expect(kline.barWidth).toBe('78%');
  });

  it('preserves business marker scatter semantics via option builder', () => {
    const option = buildMarketChartOptionFromStockPayload(payload());
    const buy = option.series.find((s) => s.name === '买入');
    const win = option.series.find((s) => s.name === '目标胜');
    expect(buy.type).toBe('scatter');
    expect(buy.data[0].value).toEqual(['20240103', 9.5]);
    expect(win.data[0].value).toEqual(['20240105', 12.1]);
    expect(option.dataZoom[0].filterMode).toBe('filter');

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
          _markerMeta: buy.data[0]._markerMeta,
        },
      },
    ]);
    expect(html).toContain('买入');
    expect(html).toContain('入场价');
    expect(html).toContain('开盘');
  });

  it('keeps a scatter point for each staged exit', () => {
    const option = buildMarketChartOptionFromStockPayload(
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
      }),
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
          _markerMeta: win.data[0]._markerMeta,
        },
      },
    ]);
    expect(html).toContain('win20%');
    expect(html).toContain('50%');
  });

  it('collapses same-day staged exits into one pin', () => {
    const option = buildMarketChartOptionFromStockPayload(
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
      }),
    );
    const win = option.series.find((s) => s.name === '目标胜');
    expect(win.data).toHaveLength(1);
    expect(win.data[0].value).toEqual(['20240105', 12.1]);
    expect(win.data[0]._markerMeta.tooltipHtml).toContain('win20%、win30%');
    expect(win.data[0]._markerMeta.tooltipHtml).toContain('100%');
  });
});
