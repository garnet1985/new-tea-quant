import React, { useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import ChartPanel from 'components/chartPanel/chartPanel';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import NtqIcon from 'components/ntqIcon/ntqIcon';
import {
  REPORT_CHART_AXIS_LABEL,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_SPLIT_LINE,
  REPORT_CHART_TOOLTIP,
} from '../../strategyWorkbenchPage/panels/strategyReportPanel/lib/reportChartsTheme';
import './strategyDesignAttributeReport.scss';

const SECTION_ORDER = [
  'opportunity',
  'stock_distribution',
  'dispersion',
  'exit_quality',
  'after_take_profit',
  'edge',
  'profit_concentration',
  'exit_profit',
];

const SECTION_TITLES = {
  opportunity: '各个参数是如何影响回测找到的机会总数？',
  stock_distribution: '各个参数是如何影响机会的在股票间的分布？',
  dispersion: '各个参数是如何影响单只票的所有机会在回测区间的分散度？',
  exit_quality: '止损与止盈的不同取值是如何影响股票亏损与盈利的比例？',
  after_take_profit: '止盈后面还有没有涨（仅当分档或动态止盈真跑过）',
  edge: '去噪后每个代表机会等权投一笔，整体能不能赚、赚得够不够？',
  profit_concentration: '利润是不是靠少数几笔 / 少数票撑起来的（是否普遍）？',
  exit_profit: '钱从止盈 / 止损 / 到期哪边来？（只描述结构）',
};

function asList(value) {
  return Array.isArray(value) ? value : [];
}

function nestedReport(payload) {
  const report = payload?.report;
  if (report && typeof report === 'object') {
    const inner = report.report;
    if (inner && typeof inner === 'object' && inner.sections) {
      return inner;
    }
    return report;
  }
  return {};
}

function resolveSections(payload, summary) {
  if (payload?.sections && typeof payload.sections === 'object') {
    return payload.sections;
  }
  if (summary?.sections && typeof summary.sections === 'object') {
    return summary.sections;
  }
  return {};
}

const PORTFOLIO_SCOPE_NOTE = (
  '本层只归因资金分配（槽位、单票上限、分配方式）。'
  + '策略参数是否普遍能赚钱，看上一层价格报告；'
  + '这里看这些分配设置有没有让账户抓住价格层里能赚钱的机会。'
);
const PORTFOLIO_SKIPPED_STRATEGY = '信号、过滤、止盈止损的对照不在本层排名。';

function isPortfolioReport(payload) {
  const step = String(payload?.step || payload?.layer || '').trim();
  return step === 'portfolio';
}

function isAllocationKnob(knob) {
  return String(knob || '').startsWith('portfolio.');
}

function resolveScopeNote(payload, summary) {
  const fromReport = String(
    payload?.scope_note || summary?.scope_note || '',
  ).trim();
  if (fromReport) return fromReport;
  const mode = String(
    payload?.analysis_mode
    || summary.analysis_mode
    || payload?.mode
    || summary.mode
    || '',
  ).trim();
  if (mode === 'cross') {
    // TODO: 全轴 cross 能展开，但报告仍按单因素讲，产品还没完成。
    return '联合/交叉扫描：多个参数同时变化时的共同影响。';
  }
  return '单因素扫描：每次只改一个参数，其余保持当前配置；看曲线与敏感度排名决定该调多少。';
}

function resolveSweeps(payload, summary) {
  const sweeps = payload?.sweeps || summary?.sweeps;
  return Array.isArray(sweeps) ? sweeps : [];
}

function resolveSensitivityRank(payload, summary) {
  const rank = payload?.sensitivity_rank || summary?.sensitivity_rank;
  return Array.isArray(rank) ? rank : [];
}

function EffectConclusion({ effect }) {
  const label = String(effect?.knob_label || '').trim()
    || String(effect?.knob || '').split('.').pop()
    || '参数';
  const outcome = String(effect?.outcome_label || '').trim();
  const lines = [
    String(effect?.max_line || '').trim(),
    String(effect?.min_line || '').trim(),
    String(effect?.trend_line || '').trim(),
  ].filter(Boolean);
  if (!lines.length) return null;

  return (
    <Box className="ntq-design-attr-report__effect-conclusion">
      <Typography variant="body2" className="ntq-design-attr-report__effect-name">
        {label}
        {outcome ? (
          <Typography component="span" variant="caption" className="ntq-design-attr-report__effect-outcome">
            {` · ${outcome}`}
          </Typography>
        ) : null}
      </Typography>
      <Stack spacing={0.3} component="ul" className="ntq-design-attr-report__list">
        {lines.map((line) => (
          <Typography
            key={line}
            component="li"
            variant="body2"
            className="ntq-design-attr-report__list-item"
          >
            {line}
          </Typography>
        ))}
      </Stack>
    </Box>
  );
}

EffectConclusion.propTypes = {
  effect: PropTypes.object.isRequired,
};

function EffectTable({ effect }) {
  const table = asList(effect?.table).filter((row) => row && typeof row === 'object');
  if (!table.length) return null;
  const knob = String(effect?.knob_label || '').trim()
    || String(effect?.knob || '').split('.').pop()
    || '参数';
  const outcome = String(effect?.outcome_label || effect?.outcome || '').trim() || '结果';

  return (
    <Box className="ntq-design-attr-report__effect-table">
      <Typography variant="caption" className="ntq-design-attr-report__effect-table-title">
        {knob}
        {outcome ? ` · ${outcome}` : ''}
      </Typography>
      <Box className="ntq-design-attr-report__table-wrap ntq-design-attr-report__table-wrap--effect">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{`当${knob}为`}</TableCell>
              <TableCell>{outcome}</TableCell>
              <TableCell>与当前策略配置的变化</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {table.map((row) => (
              <TableRow
                key={`${String(row.value_label)}-${String(row.metric_label)}`}
                className={row.is_baseline ? 'ntq-design-attr-report__row--baseline' : undefined}
              >
                <TableCell>{row.value_label ?? '—'}</TableCell>
                <TableCell>{row.metric_label ?? '—'}</TableCell>
                <TableCell>{row.delta_label ?? '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}

EffectTable.propTypes = {
  effect: PropTypes.object.isRequired,
};

function DetailsBlock({ effects }) {
  const [open, setOpen] = useState(false);
  const usable = asList(effects).filter(
    (item) => item && typeof item === 'object' && asList(item.table).length > 0,
  );
  if (!usable.length) return null;

  return (
    <Accordion
      expanded={open}
      onChange={(_event, next) => setOpen(next)}
      disableGutters
      elevation={0}
      className="ntq-design-attr-report__details"
    >
      <AccordionSummary
        expandIcon={<NtqIcon name="expandMore" size={18} />}
        className="ntq-design-attr-report__details-summary"
      >
        <Typography variant="body2" className="ntq-design-attr-report__label">
          具体细节
        </Typography>
      </AccordionSummary>
      <AccordionDetails className="ntq-design-attr-report__details-body">
        <Stack spacing={1.25}>
          {usable.map((effect) => (
            <EffectTable
              key={`${effect.knob || ''}-${effect.outcome || ''}`}
              effect={effect}
            />
          ))}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

DetailsBlock.propTypes = {
  effects: PropTypes.array,
};

function ThemeSection({ sectionKey, block }) {
  const [open, setOpen] = useState(true);
  const title = String(block?.question || '').trim()
    || SECTION_TITLES[sectionKey]
    || sectionKey;
  const effects = asList(block?.effects).filter((item) => item && typeof item === 'object');
  const baselineFacts = asList(block?.facts)
    .map((item) => String(item || '').trim())
    .filter((line) => line && !line.includes('— 最好情况') && !line.includes('最好情况：'));
  // 有 effects 时，facts 里可能混了阶梯摘要；结论区优先展示非阶梯的基准事实
  const summaryFacts = effects.length
    ? asList(block?.facts)
      .map((item) => String(item || '').trim())
      .filter((line) => line && !line.includes('最好情况') && !line.includes('最差情况') && !line.includes('趋势：'))
    : [];
  const fallback = String(block?.conclusion || '').trim();

  return (
    <Accordion
      expanded={open}
      onChange={(_event, next) => setOpen(next)}
      disableGutters
      elevation={0}
      className="ntq-design-attr-report__theme"
    >
      <AccordionSummary
        expandIcon={<NtqIcon name="expandMore" size={20} />}
        className="ntq-design-attr-report__theme-summary"
      >
        <Typography variant="subtitle2" className="ntq-design-attr-report__section-title">
          {title}
        </Typography>
      </AccordionSummary>
      <AccordionDetails className="ntq-design-attr-report__theme-body">
        <Box className="ntq-design-attr-report__conclusion-block">
          <Typography variant="body2" className="ntq-design-attr-report__label">
            结论
          </Typography>
          {summaryFacts.length ? (
            <Stack spacing={0.35} component="ul" className="ntq-design-attr-report__list">
              {summaryFacts.map((line) => (
                <Typography
                  key={line}
                  component="li"
                  variant="body2"
                  className="ntq-design-attr-report__list-item"
                >
                  {line}
                </Typography>
              ))}
            </Stack>
          ) : null}
          {effects.length ? (
            <Stack spacing={1} className="ntq-design-attr-report__conclusion-list">
              {effects.map((effect) => (
                <EffectConclusion
                  key={`${effect.knob || ''}-${effect.outcome || ''}`}
                  effect={effect}
                />
              ))}
            </Stack>
          ) : (!summaryFacts.length ? (
            <Typography variant="body2" color="text.secondary">
              {fallback || baselineFacts[0] || '暂无结论。'}
            </Typography>
          ) : null)}
        </Box>
        <DetailsBlock effects={effects} />
      </AccordionDetails>
    </Accordion>
  );
}

ThemeSection.propTypes = {
  sectionKey: PropTypes.string.isRequired,
  block: PropTypes.object.isRequired,
};

function displayKnobValue(value) {
  const text = value == null ? '' : String(value).trim();
  if (text === '未使用') return '不使用';
  return text || '—';
}

function sweepKey(knob, outcome) {
  return `${String(knob || '')}::${String(outcome || '')}`;
}

function trendForSweep(sweep, sections) {
  const knob = String(sweep?.knob || '');
  const outcome = String(sweep?.primary_outcome || '');
  if (!knob || !sections || typeof sections !== 'object') return '';
  const blocks = Object.values(sections);
  for (let i = 0; i < blocks.length; i += 1) {
    const block = blocks[i];
    if (!block || typeof block !== 'object') continue;
    const hit = asList(block.effects).find((effect) => (
      String(effect?.knob || '') === knob
      && String(effect?.outcome || '') === outcome
      && String(effect?.trend_line || '').trim()
    ));
    if (hit) {
      return String(hit.trend_line).trim().split('未使用').join('不使用');
    }
  }
  return '';
}

function omitSweepEffects(block, sweeps) {
  const covered = new Set(
    asList(sweeps)
      .filter((item) => item && item.knob && item.primary_outcome)
      .map((item) => sweepKey(item.knob, item.primary_outcome)),
  );
  if (!covered.size) return block;
  const effects = asList(block?.effects);
  const remaining = effects.filter(
    (effect) => !covered.has(sweepKey(effect?.knob, effect?.outcome)),
  );
  if (remaining.length === effects.length) return block;
  const facts = asList(block?.facts)
    .map((item) => String(item || '').trim())
    .filter((line) => (
      line
      && !line.includes('最好情况')
      && !line.includes('最差情况')
      && !line.includes('趋势：')
    ));
  return {
    ...block,
    effects: remaining,
    facts,
    conclusion: remaining.length ? block.conclusion : '',
  };
}

function sectionHasContent(block) {
  if (!block || typeof block !== 'object') return false;
  if (asList(block.effects).length) return true;
  if (asList(block.facts).some((item) => String(item || '').trim())) return true;
  if (String(block.conclusion || '').trim()) return true;
  if (block.baseline && typeof block.baseline === 'object' && Object.keys(block.baseline).length) {
    return true;
  }
  return false;
}

function isBestLevel(level, best) {
  if (!level || !best || typeof best !== 'object') return false;
  const levelLabel = level.value_label;
  const bestLabel = best.value_label;
  if (levelLabel != null && bestLabel != null && String(levelLabel) !== '' && String(bestLabel) !== '') {
    return String(levelLabel) === String(bestLabel);
  }
  return Object.is(level.value, best.value);
}

function levelMark(level, best) {
  if (isBestLevel(level, best)) return 'best';
  if (level?.is_baseline) return 'baseline';
  return '';
}

const SWEEP_LINE = '#93c5fd';
const SWEEP_CURRENT = '#fcd34d';
const SWEEP_BEST = '#4ade80';

function buildSweepChartOption(sweep, levels, outcome) {
  const metricLabel = sweep?.primary_outcome_label || outcome || '指标';
  const lineData = [];
  const currentData = [];
  const bestData = [];
  levels.forEach((level) => {
    const value = Number(level.metrics[outcome]);
    const mark = levelMark(level, sweep.best);
    lineData.push({ value, symbolSize: mark ? 0 : 8 });
    currentData.push(mark === 'baseline' ? value : null);
    bestData.push(mark === 'best' ? value : null);
  });

  return {
    animation: false,
    grid: { left: 48, right: 16, top: 36, bottom: 28 },
    legend: {
      top: 0,
      right: 8,
      itemWidth: 8,
      itemHeight: 8,
      icon: 'circle',
      selectedMode: false,
      textStyle: { color: 'rgba(255, 255, 255, 0.84)', fontSize: 12 },
      data: ['当前取值', '最佳取值'],
    },
    tooltip: {
      ...REPORT_CHART_TOOLTIP,
      trigger: 'axis',
      formatter: (params) => {
        const list = Array.isArray(params) ? params : [params];
        const point = list.find((item) => item && item.seriesType === 'line')
          || list.find((item) => item && item.value != null);
        if (!point) return '';
        const level = levels[point.dataIndex];
        if (!level) return '';
        const mark = levelMark(level, sweep.best);
        let tag = '';
        if (mark === 'best' && level.is_baseline) tag = '（当前，最佳）';
        else if (mark === 'best') tag = '（最佳）';
        else if (mark === 'baseline') tag = '（当前）';
        const raw = point.value && typeof point.value === 'object' ? point.value.value : point.value;
        return `${displayKnobValue(level.value_label)}${tag}<br/>${metricLabel}：${raw}`;
      },
    },
    xAxis: {
      type: 'category',
      data: levels.map((_, index) => String(index)),
      axisTick: { show: false },
      axisLine: REPORT_CHART_AXIS_LINE,
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL,
        formatter: (raw) => {
          const level = levels[Number(raw)];
          if (!level) return '';
          const text = displayKnobValue(level.value_label);
          const mark = levelMark(level, sweep.best);
          if (mark === 'best') return `{best|${text}}`;
          if (mark === 'baseline') return `{current|${text}}`;
          return text;
        },
        rich: {
          best: { color: SWEEP_BEST, fontSize: 11, fontWeight: 650 },
          current: { color: SWEEP_CURRENT, fontSize: 11, fontWeight: 650 },
        },
      },
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: REPORT_CHART_AXIS_LABEL,
      splitLine: REPORT_CHART_SPLIT_LINE,
    },
    series: [
      {
        name: metricLabel,
        type: 'line',
        data: lineData,
        symbol: 'circle',
        showSymbol: true,
        lineStyle: { width: 2, color: SWEEP_LINE },
        itemStyle: { color: SWEEP_LINE },
        z: 2,
      },
      {
        name: '当前取值',
        type: 'scatter',
        data: currentData,
        symbol: 'circle',
        symbolSize: 11,
        itemStyle: { color: SWEEP_CURRENT },
        z: 3,
      },
      {
        name: '最佳取值',
        type: 'scatter',
        data: bestData,
        symbol: 'circle',
        symbolSize: 11,
        itemStyle: { color: SWEEP_BEST },
        z: 4,
      },
    ],
  };
}

function SweepCurve({ sweep }) {
  const outcome = sweep?.primary_outcome || '';
  const levels = asList(sweep?.levels).filter((level) => {
    const metrics = level?.metrics && typeof level.metrics === 'object' ? level.metrics : {};
    return Number.isFinite(Number(metrics[outcome]));
  });
  if (levels.length < 2) return null;

  return (
    <ChartPanel
      option={buildSweepChartOption(sweep, levels, outcome)}
      height={200}
      framed={false}
    />
  );
}

SweepCurve.propTypes = {
  sweep: PropTypes.object.isRequired,
};

function SweepPanel({ rank, sweeps, scopeNote, sections }) {
  const usableRank = asList(rank).filter((item) => item && typeof item === 'object');
  const usableSweeps = asList(sweeps).filter(
    (item) => item && typeof item === 'object' && asList(item.levels).length >= 2,
  );
  if (!usableRank.length && !usableSweeps.length) {
    if (!scopeNote) return null;
    return (
      <Alert
        severity="info"
        variant="outlined"
        className="ntq-design-attr-report__scope-alert"
      >
        {scopeNote}
      </Alert>
    );
  }

  const outcomeLabel = String(
    usableSweeps.find((item) => item.primary_outcome_label)?.primary_outcome_label
    || '',
  ).trim() || '主指标';

  return (
    <Stack spacing={2.5} className="ntq-design-attr-report__sweeps">
      {scopeNote ? (
        <Alert
          severity="info"
          variant="outlined"
          className="ntq-design-attr-report__scope-alert"
        >
          {scopeNote}
        </Alert>
      ) : null}
      {usableRank.length ? (
        <Box>
          <Stack
            direction="row"
            spacing={0.75}
            alignItems="center"
            className="ntq-design-attr-report__rank-heading-row"
          >
            <Typography component="h3" className="ntq-design-attr-report__rank-heading">
              敏感度排名
            </Typography>
            <NtqHelpTooltip
              title={`当其余参数不变，只变动当前的参数时，「${outcomeLabel}」在不同取值间的差异，影响程度以及最优的取值。`}
              shine
              placement="top"
            />
          </Stack>
          <Box className="ntq-design-attr-report__table-wrap">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  <TableCell>参数</TableCell>
                  <TableCell>{`${outcomeLabel}的差异`}</TableCell>
                  <TableCell>{`对${outcomeLabel}的影响`}</TableCell>
                  <TableCell>{`${outcomeLabel}最优取值`}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {usableRank.map((item) => (
                  <TableRow key={`${item.rank}-${item.knob}`}>
                    <TableCell>{item.rank ?? '—'}</TableCell>
                    <TableCell>{item.knob_label || item.knob || '—'}</TableCell>
                    <TableCell>{item.span_label ?? item.span ?? '—'}</TableCell>
                    <TableCell>{item.impact || '—'}</TableCell>
                    <TableCell>
                      {displayKnobValue(item.best_value_label ?? item.best_value)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Box>
      ) : null}
      {usableSweeps.map((sweep, index) => {
        const outcome = sweep.primary_outcome || '';
        const levels = asList(sweep.levels);
        const knobLabel = sweep.knob_label || sweep.knob || '参数';
        const metricLabel = sweep.primary_outcome_label || outcome || outcomeLabel;
        const trend = trendForSweep(sweep, sections);
        return (
          <Box key={sweep.knob || sweep.knob_label} className="ntq-design-attr-report__sweep-block">
            <Stack
              direction="row"
              spacing={0.75}
              alignItems="center"
              className="ntq-design-attr-report__sweep-head"
            >
              <Typography component="h3" className="ntq-design-attr-report__sweep-title">
                {`参数 ${index + 1}: ${knobLabel}`}
              </Typography>
              <NtqHelpTooltip
                title={`只改这个参数时，「${metricLabel}」怎么变`}
                shine
                placement="top"
              />
            </Stack>
            <SweepCurve sweep={sweep} />
            {trend ? (
              <Typography variant="body2" className="ntq-design-attr-report__sweep-trend">
                {trend}
              </Typography>
            ) : null}
            <Box className="ntq-design-attr-report__table-wrap">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>取值</TableCell>
                    <TableCell>{metricLabel}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {levels.map((level) => {
                    const metrics = level?.metrics && typeof level.metrics === 'object'
                      ? level.metrics
                      : {};
                    const metric = metrics[outcome];
                    const mark = levelMark(level, sweep.best);
                    let tag = '';
                    if (mark === 'best' && level.is_baseline) tag = '（当前，最佳）';
                    else if (mark === 'best') tag = '（最佳）';
                    else if (mark === 'baseline') tag = '（当前）';
                    return (
                      <TableRow
                        key={`${String(level.value_label)}-${String(metric)}`}
                        className={mark ? `ntq-design-attr-report__row--${mark}` : undefined}
                      >
                        <TableCell>
                          {displayKnobValue(level.value_label)}
                          {tag}
                        </TableCell>
                        <TableCell>{metric == null ? '—' : String(metric)}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Box>
          </Box>
        );
      })}
    </Stack>
  );
}

SweepPanel.propTypes = {
  rank: PropTypes.array,
  sweeps: PropTypes.array,
  scopeNote: PropTypes.string,
  sections: PropTypes.object,
};

function QuestionSections({ sections, sweeps }) {
  const known = SECTION_ORDER
    .map((key) => ({ key, block: omitSweepEffects(sections[key], sweeps) }))
    .filter(({ key, block }) => {
      if (!block || typeof block !== 'object') return false;
      if (key === 'after_take_profit' && block.available !== true) return false;
      return sectionHasContent(block);
    });
  const extras = Object.keys(sections || {})
    .filter((key) => !SECTION_ORDER.includes(key))
    .map((key) => ({ key, block: omitSweepEffects(sections[key], sweeps) }))
    .filter(({ block }) => sectionHasContent(block));
  const ordered = [...known, ...extras];

  if (!ordered.length) return null;

  return (
    <Stack spacing={1.75} className="ntq-design-attr-report__sections">
      <Typography variant="subtitle2" className="ntq-design-attr-report__section-title">
        层内诊断
      </Typography>
      {ordered.map(({ key, block }) => (
        <ThemeSection key={key} sectionKey={key} block={block} />
      ))}
    </Stack>
  );
}

QuestionSections.propTypes = {
  sections: PropTypes.object.isRequired,
  sweeps: PropTypes.array,
};

/**
 * 战役归因报告（只读；不做版本对比）。
 */
function StrategyDesignAttributeReport({
  payload = null,
  loading = false,
  error = '',
  busy = false,
}) {
  const summary = useMemo(() => nestedReport(payload), [payload]);
  const portfolioLayer = isPortfolioReport(payload);
  const scopeNote = useMemo(() => {
    if (!portfolioLayer) return resolveScopeNote(payload, summary);
    const rawRank = resolveSensitivityRank(payload, summary);
    const dropped = rawRank.some((item) => item && !isAllocationKnob(item.knob));
    return dropped
      ? `${PORTFOLIO_SCOPE_NOTE}${PORTFOLIO_SKIPPED_STRATEGY}`
      : PORTFOLIO_SCOPE_NOTE;
  }, [payload, portfolioLayer, summary]);
  const sections = useMemo(
    () => resolveSections(payload, summary),
    [payload, summary],
  );
  const sweeps = useMemo(() => {
    const rows = resolveSweeps(payload, summary);
    if (!portfolioLayer) return rows;
    return rows.filter((item) => isAllocationKnob(item?.knob));
  }, [payload, portfolioLayer, summary]);
  const rank = useMemo(() => {
    const rows = resolveSensitivityRank(payload, summary);
    if (!portfolioLayer) return rows;
    return rows.filter((item) => isAllocationKnob(item?.knob));
  }, [payload, portfolioLayer, summary]);
  const hasSections = Object.keys(sections).length > 0;
  const hasSweeps = sweeps.length > 0 || rank.length > 0;
  const upstreamBridge = String(
    payload?.upstream_bridge || summary?.upstream_bridge || '',
  ).trim();

  if (loading) {
    return (
      <Box className="ntq-design-attr-report ntq-design-attr-report--center">
        <CircularProgress size={28} />
        <Typography variant="body2" color="text.secondary">正在读取归因报告…</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" className="ntq-design-attr-report__alert">
        {error}
      </Alert>
    );
  }

  if (!payload) {
    return (
      <Box className="ntq-design-attr-report ntq-design-attr-report--empty">
        <Typography variant="body2" color="text.secondary">
          {busy
            ? '归因进行中，完成后会显示在这里。'
            : '尚未运行归因。配置 attribution.py 后，点击上方「开始归因」。'}
        </Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={1.5} className="ntq-design-attr-report">
      {upstreamBridge ? (
        <Alert
          severity="info"
          variant="outlined"
          className="ntq-design-attr-report__scope-alert"
        >
          {upstreamBridge}
        </Alert>
      ) : null}
      {hasSweeps || (portfolioLayer && scopeNote) ? (
        <SweepPanel
          rank={rank}
          sweeps={sweeps}
          scopeNote={scopeNote}
          sections={sections}
        />
      ) : null}
      {hasSections ? (
        <QuestionSections sections={sections} sweeps={sweeps} />
      ) : null}
      {!hasSweeps && !hasSections ? (
        <Typography variant="body2" color="text.secondary">
          已有归因产物，但没有可展示的摘要字段。重新跑一遍归因后会按扫描与主题展示。
        </Typography>
      ) : null}
    </Stack>
  );
}

StrategyDesignAttributeReport.propTypes = {
  payload: PropTypes.object,
  loading: PropTypes.bool,
  error: PropTypes.string,
  busy: PropTypes.bool,
};

export default StrategyDesignAttributeReport;
