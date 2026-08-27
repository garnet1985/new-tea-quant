import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { Box, Stack, Typography } from '@mui/material';
import ChartPanel from 'components/chartPanel/chartPanel';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import MetricCard from 'components/metricCard/metricCard';
import MetricGrid from 'components/metricGrid/metricGrid';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import ReportUnavailableHint from '../components/reportUnavailableHint';
import {
  ANALYSIS_CHART_TIPS,
  ANALYSIS_METRIC_TIPS,
  ANALYSIS_SECTION_TIPS,
} from '../reportMetricTips';
import {
  ANALYSIS_BINS_TITLE,
  ANALYSIS_CONCLUSION_TITLE,
  ANALYSIS_DIRECTION_CAPTION,
  ANALYSIS_EMPTY_CAPTURE_Q,
  ANALYSIS_EMPTY_HIT_BADGE,
  ANALYSIS_EMPTY_LEAD_ZH,
  ANALYSIS_EMPTY_SAMPLE_Q,
  ANALYSIS_EMPTY_TITLE,
  ANALYSIS_EMPTY_ZH,
  ANALYSIS_ERROR_ZH,
  ANALYSIS_EXPLAIN_CAPTION,
  ANALYSIS_LOADING_ZH,
  ANALYSIS_MISSING_ZH,
  ANALYSIS_MULTIVARIATE_TITLE,
  ANALYSIS_NOT_EXPLAIN_CAPTION,
  ANALYSIS_OTHER_FIELDS_TITLE,
  ANALYSIS_OVERVIEW_TITLE,
  ANALYSIS_PRIMARY_FIELD_CAPTION,
  ANALYSIS_RUN_COMPARISON_TITLE,
  ANALYSIS_SAMPLE_CAPTION,
  ANALYSIS_SECTION_TITLE,
  ANALYSIS_SIGNIFICANCE_CAPTION,
  ANALYSIS_SKIP_CAPTION,
  ANALYSIS_TIER_COL_N,
  ANALYSIS_TIER_COL_RANGE,
  ANALYSIS_TIER_COL_ROI,
  ANALYSIS_TIER_COL_WIN,
  ANALYSIS_TIERS_TITLE,
  ANALYSIS_WATERSHED_TITLE,
  analysisEmptyCaptureDetail,
  analysisEmptySampleDetail,
} from '../reportSectionMeta';
import {
  buildRoiBarOption,
  correlationDirection,
  formatCount,
  formatNum,
  formatPlain,
  formatPValue,
  formatRoiPct,
  formatWinPct,
  maxAbs,
  multivariateKindLabel,
  rankFillPct,
  sameBinning,
  sampleSizeFromFacts,
  significanceLabel,
} from '../lib/analysisFactsDisplay';

function RankRows({ rows, valueKey, formatValue }) {
  const peak = maxAbs(rows.map((row) => row?.[valueKey]));
  if (!rows.length) return null;
  return (
    <Stack spacing={0.75} className="ntq-analysis-rank-list">
      {rows.map((row) => {
        if (!row || typeof row !== 'object') return null;
        const key = String(row.key || '?');
        const raw = row[valueKey];
        const n = Number(raw);
        const neg = Number.isFinite(n) && n < 0;
        return (
          <Box key={key} className="ntq-analysis-rank">
            <Typography variant="body2" className="ntq-analysis-rank__label" noWrap title={key}>
              {key}
            </Typography>
            <Box className="ntq-analysis-rank__track">
              <Box
                className={`ntq-analysis-rank__fill${neg ? ' ntq-analysis-rank__fill--neg' : ''}`}
                style={{ width: `${rankFillPct(raw, peak)}%` }}
              />
            </Box>
            <Typography variant="body2" className="ntq-analysis-rank__value">
              {formatValue(raw)}
            </Typography>
          </Box>
        );
      })}
    </Stack>
  );
}

RankRows.propTypes = {
  rows: PropTypes.arrayOf(PropTypes.object).isRequired,
  valueKey: PropTypes.string.isRequired,
  formatValue: PropTypes.func.isRequired,
};

function FindingList({ items }) {
  const rows = Array.isArray(items) ? items.filter((item) => item && typeof item === 'object') : [];
  if (!rows.length) return null;
  return (
    <Stack spacing={0.5} className="ntq-analysis-findings">
      {rows.map((item, idx) => {
        const caption = String(item.caption || '').trim();
        const value = String(item.value || '').trim();
        const line = caption && value ? `${caption}：${value}` : (caption || value);
        if (!line) return null;
        return (
          <Typography key={`${line}-${idx}`} variant="body2" color="text.primary">
            {`· ${line}`}
          </Typography>
        );
      })}
    </Stack>
  );
}

FindingList.propTypes = {
  items: PropTypes.arrayOf(PropTypes.object),
};

FindingList.defaultProps = {
  items: [],
};

function EmptyCheckCard({ question, detail, isHit }) {
  return (
    <Box className={`ntq-analysis-empty-check${isHit ? ' ntq-analysis-empty-check--hit' : ''}`}>
      <Stack direction="row" spacing={0.75} alignItems="baseline" sx={{ mb: 0.35 }}>
        <Typography variant="body2" fontWeight={600} color="text.primary">
          {question}
        </Typography>
        {isHit ? (
          <Typography variant="caption" className="ntq-analysis-empty-check__badge">
            {ANALYSIS_EMPTY_HIT_BADGE}
          </Typography>
        ) : null}
      </Stack>
      <Typography variant="body2" color="text.secondary">
        {detail}
      </Typography>
    </Box>
  );
}

EmptyCheckCard.propTypes = {
  question: PropTypes.string.isRequired,
  detail: PropTypes.string.isRequired,
  isHit: PropTypes.bool,
};

EmptyCheckCard.defaultProps = {
  isHit: false,
};

function EmptyChecks({ reason }) {
  const block = reason && typeof reason === 'object' ? reason : {};
  const code = String(block.code || 'unknown');
  const investmentCount = Number(block.investment_count) || 0;
  const withSnapshot = Number(block.with_snapshot) || 0;
  const sampleHit = code === 'insufficient_samples';
  const captureHit = code === 'no_capture';
  return (
    <SectionBlock title={ANALYSIS_EMPTY_TITLE} tip={ANALYSIS_SECTION_TIPS.empty}>
      <Stack spacing={1}>
        <Typography variant="body2" color="text.secondary">
          {ANALYSIS_EMPTY_LEAD_ZH}
        </Typography>
        <EmptyCheckCard
          question={ANALYSIS_EMPTY_SAMPLE_Q}
          isHit={sampleHit}
          detail={analysisEmptySampleDetail({
            investmentCount,
            withSnapshot,
            isHit: sampleHit,
          })}
        />
        <EmptyCheckCard
          question={ANALYSIS_EMPTY_CAPTURE_Q}
          isHit={captureHit}
          detail={analysisEmptyCaptureDetail({
            investmentCount,
            withSnapshot,
            isHit: captureHit,
          })}
        />
      </Stack>
    </SectionBlock>
  );
}

EmptyChecks.propTypes = {
  reason: PropTypes.object,
};

EmptyChecks.defaultProps = {
  reason: null,
};

function NoteList({ title, items }) {
  const rows = Array.isArray(items) ? items.map((item) => String(item || '').trim()).filter(Boolean) : [];
  if (!rows.length) return null;
  return (
    <Stack spacing={0.35}>
      <Typography variant="caption" color="text.secondary">{title}</Typography>
      {rows.map((line) => (
        <Typography key={line} variant="body2" color="text.secondary">
          {`· ${line}`}
        </Typography>
      ))}
    </Stack>
  );
}

NoteList.propTypes = {
  title: PropTypes.string.isRequired,
  items: PropTypes.arrayOf(PropTypes.string),
};

NoteList.defaultProps = {
  items: [],
};

function BinTable({ rows }) {
  const list = Array.isArray(rows) ? rows.filter((row) => row && typeof row === 'object') : [];
  if (!list.length) return null;
  return (
    <Box className="ntq-analysis-tier-table" sx={{ mt: 1 }}>
      <Box className="ntq-analysis-tier-row ntq-analysis-tier-row--head">
        <span>{ANALYSIS_TIER_COL_RANGE}</span>
        <span>{ANALYSIS_TIER_COL_ROI}</span>
        <span>{ANALYSIS_TIER_COL_WIN}</span>
        <span>{ANALYSIS_TIER_COL_N}</span>
      </Box>
      {list.map((row, idx) => {
        const label = String(row.label || '?').trim() || '?';
        return (
          <Box key={`${label}-${idx}`} className="ntq-analysis-tier-row">
            <span>{label}</span>
            <span>{formatRoiPct(row.mean_roi)}</span>
            <span>{formatWinPct(row.win_rate)}</span>
            <span>{formatCount(row.count)}</span>
          </Box>
        );
      })}
    </Box>
  );
}

BinTable.propTypes = {
  rows: PropTypes.arrayOf(PropTypes.object),
};

BinTable.defaultProps = {
  rows: [],
};

function StepAnalysisInsights({ status, analysis, error = '' }) {
  const facts = useMemo(() => {
    if (!analysis?.enabled || !analysis?.facts || typeof analysis.facts !== 'object') {
      return null;
    }
    return analysis.facts;
  }, [analysis]);
  const conclusion = useMemo(() => {
    if (!analysis?.enabled || !analysis?.conclusion || typeof analysis.conclusion !== 'object') {
      return null;
    }
    return analysis.conclusion;
  }, [analysis]);

  const corr = facts?.correlation && typeof facts.correlation === 'object'
    ? facts.correlation
    : null;
  const direction = correlationDirection(corr?.rho);
  const significance = significanceLabel(corr?.p_value);
  const tiers = Array.isArray(facts?.tiers) ? facts.tiers.filter((t) => t && typeof t === 'object') : [];
  const buckets = Array.isArray(facts?.buckets) ? facts.buckets.filter((t) => t && typeof t === 'object') : [];
  const otherFields = Array.isArray(facts?.other_fields)
    ? facts.other_fields.filter((row) => row && typeof row === 'object')
    : [];
  const multivariate = facts?.multivariate && typeof facts.multivariate === 'object'
    ? facts.multivariate
    : null;
  const mvRanking = Array.isArray(multivariate?.ranking)
    ? multivariate.ranking.filter((row) => row && typeof row === 'object')
    : [];
  const runComparison = facts?.run_comparison && typeof facts.run_comparison === 'object'
    ? facts.run_comparison
    : null;
  const settingsDiff = Array.isArray(runComparison?.settings_diff)
    ? runComparison.settings_diff.filter((row) => row && typeof row === 'object')
    : [];
  const skip = facts?.skip_summary && typeof facts.skip_summary === 'object'
    ? facts.skip_summary
    : null;
  const skipped = Number(skip?.skipped_count) || 0;
  const sampleSize = sampleSizeFromFacts(facts);
  const watershedDistinct = tiers.length > 0 && !sameBinning(tiers, buckets);
  const watershedOption = useMemo(
    () => (watershedDistinct ? buildRoiBarOption(tiers, { barMaxWidth: 56 }) : null),
    [watershedDistinct, tiers],
  );
  const binsOption = useMemo(
    () => (buckets.length > 0
      ? buildRoiBarOption(buckets, { barMaxWidth: buckets.length > 4 ? 22 : 36, rotate: buckets.length > 4 ? 20 : 0 })
      : null),
    [buckets],
  );
  const showOverview = Boolean(
    facts?.field_key || (corr && corr.status === 'ok') || sampleSize != null || skipped > 0,
  );
  const showMultivariate = (multivariate?.status === 'ok' || multivariate?.status === 'partial')
    && mvRanking.length > 0;
  const showCompare = runComparison?.status === 'ok' && settingsDiff.length > 0;
  const showConclusion = facts?.status !== 'empty' && Boolean(
    conclusion?.headline
    || (Array.isArray(conclusion?.key_findings) && conclusion.key_findings.length)
    || (Array.isArray(conclusion?.explains) && conclusion.explains.length)
    || (Array.isArray(conclusion?.does_not_explain) && conclusion.does_not_explain.length),
  );
  const showBinCharts = Boolean(watershedOption || binsOption);

  if (status === 'idle') return null;
  if (analysis && analysis.enabled === false) return null;

  return (
    <Box className="ntq-step-analysis">
      <Stack direction="row" spacing={0.5} alignItems="center" className="ntq-step-analysis__title">
        <Typography variant="subtitle2" fontWeight={600}>
          {ANALYSIS_SECTION_TITLE}
        </Typography>
        <NtqHelpTooltip title={ANALYSIS_SECTION_TIPS.root} />
      </Stack>
      {status === 'loading' ? (
        <InlineLoadingState compact block message={ANALYSIS_LOADING_ZH} />
      ) : null}
      {status === 'error' ? (
        <Typography variant="body2" color="error" sx={{ py: 0.5 }}>
          {error || ANALYSIS_ERROR_ZH}
        </Typography>
      ) : null}
      {status === 'missing' ? (
        <ReportUnavailableHint message={ANALYSIS_MISSING_ZH} />
      ) : null}
      {status === 'ok' && facts ? (
        <Stack spacing={1.25} className="ntq-step-analysis__body">
          {facts.status === 'empty' ? (
            <EmptyChecks reason={facts.empty_reason} />
          ) : null}

          {showConclusion ? (
            <SectionBlock title={ANALYSIS_CONCLUSION_TITLE} tip={ANALYSIS_SECTION_TIPS.conclusion}>
              <Stack spacing={1}>
                {conclusion.headline ? (
                  <Typography variant="body2" fontWeight={600} color="text.primary">
                    {conclusion.headline}
                  </Typography>
                ) : null}
                <FindingList items={conclusion.key_findings} />
                <NoteList title={ANALYSIS_EXPLAIN_CAPTION} items={conclusion.explains} />
                <NoteList title={ANALYSIS_NOT_EXPLAIN_CAPTION} items={conclusion.does_not_explain} />
              </Stack>
            </SectionBlock>
          ) : null}

          {showOverview ? (
            <SectionBlock title={ANALYSIS_OVERVIEW_TITLE} tip={ANALYSIS_SECTION_TIPS.overview}>
              <MetricGrid columns={4} denseXs>
                {facts.field_key ? (
                  <MetricCard
                    title={ANALYSIS_PRIMARY_FIELD_CAPTION}
                    titleTip={ANALYSIS_METRIC_TIPS.fieldKey}
                    value={String(facts.field_key)}
                  />
                ) : null}
                {corr && corr.status === 'ok' ? (
                  <MetricCard
                    title={ANALYSIS_DIRECTION_CAPTION}
                    titleTip={ANALYSIS_METRIC_TIPS.direction}
                    value={direction.label}
                    hint={`ρ=${formatNum(corr.rho, 3)}`}
                  />
                ) : null}
                {corr && corr.status === 'ok' ? (
                  <MetricCard
                    title={ANALYSIS_SIGNIFICANCE_CAPTION}
                    titleTip={ANALYSIS_METRIC_TIPS.significance}
                    value={significance.label}
                    hint={`p=${formatPValue(corr.p_value)}`}
                  />
                ) : null}
                {sampleSize != null ? (
                  <MetricCard
                    title={ANALYSIS_SAMPLE_CAPTION}
                    titleTip={ANALYSIS_METRIC_TIPS.sample}
                    value={formatCount(sampleSize)}
                  />
                ) : null}
                {skipped > 0 ? (
                  <MetricCard
                    title={ANALYSIS_SKIP_CAPTION}
                    titleTip={ANALYSIS_METRIC_TIPS.skip}
                    value={`${formatCount(skipped)} / ${formatCount(skip.investment_count)}`}
                  />
                ) : null}
              </MetricGrid>
            </SectionBlock>
          ) : null}

          {showBinCharts ? (
            <SectionBlock title={ANALYSIS_TIERS_TITLE} tip={ANALYSIS_SECTION_TIPS.tiers}>
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: {
                    xs: '1fr',
                    md: watershedOption && binsOption ? '1fr 1fr' : '1fr',
                  },
                  gap: 1,
                }}
              >
                {watershedOption ? (
                  <Box>
                    <ChartPanel
                      title={ANALYSIS_WATERSHED_TITLE}
                      tip={ANALYSIS_CHART_TIPS.watershed}
                      option={watershedOption}
                    />
                    <BinTable rows={tiers} />
                  </Box>
                ) : null}
                {binsOption ? (
                  <Box>
                    <ChartPanel
                      title={ANALYSIS_BINS_TITLE}
                      tip={ANALYSIS_CHART_TIPS.bins}
                      option={binsOption}
                      height={buckets.length > 4 ? 200 : 180}
                    />
                    <BinTable rows={buckets} />
                  </Box>
                ) : null}
              </Box>
            </SectionBlock>
          ) : null}

          {otherFields.length > 0 ? (
            <SectionBlock title={ANALYSIS_OTHER_FIELDS_TITLE} tip={ANALYSIS_SECTION_TIPS.otherFields}>
              <MetricGrid columns={4} denseXs>
                {otherFields.map((row) => {
                  const dir = correlationDirection(row.rho);
                  return (
                    <MetricCard
                      key={String(row.key || '?')}
                      title={String(row.key || '?')}
                      titleTip={ANALYSIS_METRIC_TIPS.rho}
                      value={dir.label}
                      hint={`ρ=${formatNum(row.rho, 2)}`}
                    />
                  );
                })}
              </MetricGrid>
            </SectionBlock>
          ) : null}

          {showMultivariate ? (
            <SectionBlock title={ANALYSIS_MULTIVARIATE_TITLE} tip={ANALYSIS_SECTION_TIPS.multivariate}>
              {multivariateKindLabel(mvRanking[0]?.kind) ? (
                <Typography variant="caption" color="text.secondary">
                  {multivariateKindLabel(mvRanking[0].kind)}
                </Typography>
              ) : null}
              <RankRows
                rows={mvRanking}
                valueKey="coef"
                formatValue={(v) => formatNum(v, 3)}
              />
            </SectionBlock>
          ) : null}

          {showCompare ? (
            <SectionBlock title={ANALYSIS_RUN_COMPARISON_TITLE} tip={ANALYSIS_SECTION_TIPS.runComparison}>
              <Stack spacing={0.75}>
                {settingsDiff.map((row) => {
                  const key = String(row.key || '?');
                  return (
                    <Box key={key} className="ntq-analysis-diff">
                      <Typography variant="body2" className="ntq-analysis-diff__key">{key}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {`${formatPlain(row.baseline)} → ${formatPlain(row.current)}`}
                      </Typography>
                    </Box>
                  );
                })}
              </Stack>
            </SectionBlock>
          ) : null}
        </Stack>
      ) : null}
      {status === 'ok' && !facts ? (
        <ReportUnavailableHint message={ANALYSIS_EMPTY_ZH} />
      ) : null}
    </Box>
  );
}

StepAnalysisInsights.propTypes = {
  status: PropTypes.oneOf(['idle', 'loading', 'ok', 'missing', 'error']).isRequired,
  analysis: PropTypes.shape({
    enabled: PropTypes.bool,
    available: PropTypes.bool,
    facts: PropTypes.object,
    conclusion: PropTypes.object,
  }),
  error: PropTypes.string,
};

StepAnalysisInsights.defaultProps = {
  analysis: null,
  error: '',
};

export default StepAnalysisInsights;
