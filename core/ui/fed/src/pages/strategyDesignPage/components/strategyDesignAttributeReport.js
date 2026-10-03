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

const ENUM_SECTION_ORDER = [
  'opportunity',
  'stock_distribution',
  'dispersion',
  'exit_quality',
  'after_take_profit',
];

const ENUM_SECTION_TITLES = {
  opportunity: '各个参数是如何影响回测找到的机会总数？',
  stock_distribution: '各个参数是如何影响机会的在股票间的分布？',
  dispersion: '各个参数是如何影响单只票的所有机会在回测区间的分散度？',
  exit_quality: '止损与止盈的不同取值是如何影响股票亏损与盈利的比例？',
  after_take_profit: '止盈后面还有没有涨（仅当分档或动态止盈真跑过）',
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
  const mode = String(
    payload?.analysis_mode
    || summary.analysis_mode
    || payload?.mode
    || summary.mode
    || '',
  ).trim();
  if (mode === 'cross') {
    return '当前归因为多个参数对结果的共同影响归因';
  }
  // oaat / inputs / 缺省：单参数归因
  return '当前归因为单个参数对结果的归因';
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
  const title = ENUM_SECTION_TITLES[sectionKey]
    || String(block?.question || sectionKey).trim();
  const effects = asList(block?.effects).filter((item) => item && typeof item === 'object');
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
          {effects.length ? (
            <Stack spacing={1} className="ntq-design-attr-report__conclusion-list">
              {effects.map((effect) => (
                <EffectConclusion
                  key={`${effect.knob || ''}-${effect.outcome || ''}`}
                  effect={effect}
                />
              ))}
            </Stack>
          ) : (
            <Typography variant="body2" color="text.secondary">
              {fallback || '暂无结论。'}
            </Typography>
          )}
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

function EnumSections({ sections, scopeNote }) {
  const ordered = ENUM_SECTION_ORDER
    .map((key) => ({ key, block: sections[key] }))
    .filter(({ key, block }) => {
      if (!block || typeof block !== 'object') return false;
      if (key === 'after_take_profit' && block.available !== true) return false;
      return true;
    });

  if (!ordered.length) return null;

  return (
    <Stack spacing={1.75} className="ntq-design-attr-report__sections">
      {scopeNote ? (
        <Alert
          severity="info"
          variant="outlined"
          className="ntq-design-attr-report__scope-alert"
        >
          {scopeNote}
        </Alert>
      ) : null}
      {ordered.map(({ key, block }) => (
        <ThemeSection key={key} sectionKey={key} block={block} />
      ))}
    </Stack>
  );
}

EnumSections.propTypes = {
  sections: PropTypes.object.isRequired,
  scopeNote: PropTypes.string,
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
  const isEnum = String(payload?.step || '').trim() === 'enum'
    || String(payload?.layer || summary.layer || '').trim() === 'enumerate';
  const hasSections = isEnum && Object.keys(sections).length > 0;

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
      {hasSections ? (
        <EnumSections sections={sections} scopeNote={scopeNote} />
      ) : (
        <Typography variant="body2" color="text.secondary">
          已有归因产物，但没有可展示的摘要字段。重新跑一遍枚举归因后会按主题展示。
        </Typography>
      )}
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
