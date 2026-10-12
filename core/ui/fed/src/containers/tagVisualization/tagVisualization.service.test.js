import {
  buildTagGanttOption,
  countEntitiesByValue,
  ganttBarShape,
  parseSnapshotNote,
  snapshotBoardCards,
  tagValueColor,
} from './tagVisualization.service';

describe('tagVisualization.service', () => {
  it('puts tag names on the axis and keeps the value for hover', () => {
    const option = buildTagGanttOption([
      { lane: '低市值', value_label: '8.0亿元', start: '20240101', end: '20240601' },
      { lane: '高市值', value_label: '120.0亿元', start: '20240601', end: '20241231' },
    ], ['高市值', '中市值', '低市值']);
    expect(option.yAxis.data).toEqual(['高市值', '中市值', '低市值']);
    expect(option.series[0].data[0].value[3]).toBe('8.0亿元');
    expect(option.series[0].data[0].itemStyle.color).toBe(tagValueColor('低市值'));
    expect(option.series[0].clip).toBe(true);
    expect(option.dataZoom.every((zoom) => zoom.filterMode === 'none')).toBe(true);
  });

  it('keeps a fixed bar height and the visible slice when the interval sticks out of the window', () => {
    const window = { x: 0, y: 0, width: 100, height: 120 };
    const inside = ganttBarShape(10, 40, 50, 200, window);
    expect(inside).toEqual({ x: 10, y: 41, width: 30, height: 18 });

    const stickingOut = ganttBarShape(-80, 240, 50, 200, window);
    expect(stickingOut).toEqual({ x: 0, y: 41, width: 100, height: 18 });
  });

  it('opens on the latest six months and marks day ticks with 日', () => {
    const option = buildTagGanttOption([
      { lane: '低市值', value_label: '8.0亿元', start: '20240101', end: '20241231' },
    ]);
    expect(option.xAxis.minInterval).toBe(24 * 60 * 60 * 1000);
    expect(option.xAxis.axisLabel.formatter).toEqual({
      year: '{yyyy}年',
      month: '{M}月',
      day: '{d}日',
    });
    option.dataZoom.forEach((zoom) => {
      expect(zoom.startValue).toBe(Date.UTC(2024, 5, 30));
      expect(zoom.endValue).toBe(Date.UTC(2024, 11, 31));
      expect(zoom.filterMode).toBe('none');
    });
  });

  it('shows the whole range when the series is shorter than six months', () => {
    const option = buildTagGanttOption([
      { lane: '低市值', value_label: '8.0亿元', start: '20241001', end: '20241231' },
    ]);
    option.dataZoom.forEach((zoom) => {
      expect(zoom.startValue).toBeUndefined();
      expect(zoom.endValue).toBeUndefined();
    });
  });

  it('returns null when there is nothing to draw', () => {
    expect(buildTagGanttOption([])).toBeNull();
  });

  it('splits a snapshot note into count, places, and samples', () => {
    expect(parseSnapshotNote(
      '95只 · 云南、内蒙 · 样例 000038.SZ、000047.SZ · 未映射 18',
    )).toEqual({
      count: 95,
      provinces: ['云南', '内蒙'],
      samples: ['000038.SZ', '000047.SZ'],
      unmapped: 18,
    });
    expect(parseSnapshotNote('0只')).toEqual({
      count: 0,
      provinces: [],
      samples: [],
      unmapped: null,
    });
    expect(parseSnapshotNote('LPR 3.35（-0.10）')).toBeNull();
  });

  it('ranks snapshot cards by count and skips mixed shapes', () => {
    const board = snapshotBoardCards([
      { kind: 'scalar', tag_name: 'chengyu', tag_display_name: '成渝双城', scalar: '14只 · 四川', as_of: '20260101' },
      { kind: 'scalar', tag_name: 'yangtze', tag_display_name: '长三角', scalar: '104只 · 上海', as_of: '20260101' },
    ]);
    expect(board.total).toBe(118);
    expect(board.asOf).toBe('20260101');
    expect(board.cards.map((card) => card.name)).toEqual(['长三角', '成渝双城']);
    expect(snapshotBoardCards([
      { kind: 'scalar', scalar: '14只' },
      { kind: 'fields', fields: [] },
    ])).toBeNull();
  });

  it('counts current tags for the entity summary', () => {
    expect(countEntitiesByValue([
      { value_label: 'high' },
      { value_label: 'high' },
      { value_label: 'low' },
    ])).toEqual([
      { label: 'high', count: 2 },
      { label: 'low', count: 1 },
    ]);
  });
});
