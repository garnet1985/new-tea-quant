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
import NtqIcon from 'components/ntqIcon/ntqIcon';
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

function SweepCurve({ sweep }) {
  const outcome = sweep?.primary_outcome || '';
  const levels = asList(sweep?.levels).filter((level) => {
    const metrics = level?.metrics && typeof level.metrics === 'object' ? level.metrics : {};
    return Number.isFinite(Number(metrics[outcome]));
  });
  if (levels.length < 2) return null;

  const values = levels.map((level) => Number(level.metrics[outcome]));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = 320;
  const height = 96;
  const padX = 12;
  const padY = 14;
  const points = levels.map((level, index) => {
    const x = padX + (index / Math.max(levels.length - 1, 1)) * (width - padX * 2);
    const y = padY + (1 - (Number(level.metrics[outcome]) - min) / span) * (height - padY * 2);
    return { x, y, level, value: Number(level.metrics[outcome]) };
  });
  const polyline = points.map((point) => `${point.x},${point.y}`).join(' ');

  return (
    <Box className="ntq-design-attr-report__curve" aria-hidden={false}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="ntq-design-attr-report__curve-svg"
        role="img"
        aria-label={`${sweep.knob_label || sweep.knob || '参数'} 扫描曲线`}
      >
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          points={polyline}
          className="ntq-design-attr-report__curve-line"
        />
        {points.map((point) => (
          <circle
            key={`${point.x}-${point.y}-${point.level.value_label}`}
            cx={point.x}
            cy={point.y}
            r={point.level.is_baseline ? 4.5 : 3.2}
            className={
              point.level.is_baseline
                ? 'ntq-design-attr-report__curve-dot ntq-design-attr-report__curve-dot--baseline'
                : 'ntq-design-attr-report__curve-dot'
            }
          />
        ))}
      </svg>
      <Stack
        direction="row"
        justifyContent="space-between"
        className="ntq-design-attr-report__curve-labels"
      >
        {levels.map((level) => (
          <Typography
            key={String(level.value_label)}
            variant="caption"
            color="text.secondary"
            className={level.is_baseline ? 'ntq-design-attr-report__curve-label--baseline' : undefined}
          >
            {level.value_label ?? '—'}
          </Typography>
        ))}
      </Stack>
    </Box>
  );
}

SweepCurve.propTypes = {
  sweep: PropTypes.object.isRequired,
};

function SweepPanel({ rank, sweeps, scopeNote }) {
  const usableRank = asList(rank).filter((item) => item && typeof item === 'object');
  const usableSweeps = asList(sweeps).filter(
    (item) => item && typeof item === 'object' && asList(item.levels).length >= 2,
  );
  if (!usableRank.length && !usableSweeps.length) return null;

  return (
    <Stack spacing={1.5} className="ntq-design-attr-report__sweeps">
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
          <Typography variant="subtitle2" className="ntq-design-attr-report__section-title">
            敏感度排名
          </Typography>
          <Box className="ntq-design-attr-report__table-wrap">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  <TableCell>参数</TableCell>
                  <TableCell>起伏</TableCell>
                  <TableCell>影响</TableCell>
                  <TableCell>样本内较优</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {usableRank.map((item) => (
                  <TableRow key={`${item.rank}-${item.knob}`}>
                    <TableCell>{item.rank ?? '—'}</TableCell>
                    <TableCell>{item.knob_label || item.knob || '—'}</TableCell>
                    <TableCell>{item.span_label ?? item.span ?? '—'}</TableCell>
                    <TableCell>{item.impact || '—'}</TableCell>
                    <TableCell>{item.best_value_label ?? item.best_value ?? '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Box>
      ) : null}
      {usableSweeps.map((sweep) => {
        const outcome = sweep.primary_outcome || '';
        const levels = asList(sweep.levels);
        return (
          <Box key={sweep.knob || sweep.knob_label}>
            <Typography variant="subtitle2" className="ntq-design-attr-report__section-title">
              {`${sweep.knob_label || sweep.knob || '参数'} → ${
                sweep.primary_outcome_label || outcome || '指标'
              }`}
            </Typography>
            {sweep.advice ? (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.75 }}>
                {sweep.advice}
              </Typography>
            ) : null}
            <SweepCurve sweep={sweep} />
            <Box className="ntq-design-attr-report__table-wrap">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>取值</TableCell>
                    <TableCell>{sweep.primary_outcome_label || outcome || '指标'}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {levels.map((level) => {
                    const metrics = level?.metrics && typeof level.metrics === 'object'
                      ? level.metrics
                      : {};
                    const metric = metrics[outcome];
                    return (
                      <TableRow
                        key={`${String(level.value_label)}-${String(metric)}`}
                        className={level.is_baseline ? 'ntq-design-attr-report__row--baseline' : undefined}
                      >
                        <TableCell>
                          {level.value_label ?? '—'}
                          {level.is_baseline ? '（当前）' : ''}
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
};

function QuestionSections({ sections }) {
  const known = SECTION_ORDER
    .map((key) => ({ key, block: sections[key] }))
    .filter(({ key, block }) => {
      if (!block || typeof block !== 'object') return false;
      if (key === 'after_take_profit' && block.available !== true) return false;
      return true;
    });
  const extras = Object.keys(sections || {})
    .filter((key) => !SECTION_ORDER.includes(key))
    .map((key) => ({ key, block: sections[key] }))
    .filter(({ block }) => block && typeof block === 'object');
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
  const scopeNote = useMemo(
    () => resolveScopeNote(payload, summary),
    [payload, summary],
  );
  const sections = useMemo(
    () => resolveSections(payload, summary),
    [payload, summary],
  );
  const sweeps = useMemo(
    () => resolveSweeps(payload, summary),
    [payload, summary],
  );
  const rank = useMemo(
    () => resolveSensitivityRank(payload, summary),
    [payload, summary],
  );
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
      {hasSweeps ? (
        <SweepPanel rank={rank} sweeps={sweeps} scopeNote={scopeNote} />
      ) : null}
      {hasSections ? (
        <QuestionSections sections={sections} />
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
