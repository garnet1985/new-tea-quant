import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { Box, Stack, Typography } from '@mui/material';
import ChartPanel from 'components/chartPanel/chartPanel';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import MetricCard from 'components/metricCard/metricCard';
import MetricGrid from 'components/metricGrid/metricGrid';
import { SectionBlock, SectionTitle } from 'components/sectionBlock/sectionBlock';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import ReportUnavailableHint from '../components/reportUnavailableHint';
import {
  ANALYSIS_CHART_TIPS,
  ANALYSIS_METRIC_TIPS,
  ANALYSIS_SECTION_TIPS,
} from '../reportMetricTips';
import {
  ANALYSIS_BINS_TITLE,
  ANALYSIS_EMPTY_CAPTURE_Q,
  ANALYSIS_EMPTY_HIT_BADGE,
  ANALYSIS_EMPTY_LEAD_ZH,
  ANALYSIS_EMPTY_SAMPLE_Q,
  ANALYSIS_EMPTY_TITLE,
  ANALYSIS_EMPTY_ZH,
  ANALYSIS_ERROR_ZH,
  ANALYSIS_EXPLAIN_BOX_TITLE,
  ANALYSIS_FINDINGS_TITLE,
  ANALYSIS_HERO_READ_TITLE,
  ANALYSIS_LOADING_ZH,
  ANALYSIS_MISSING_ZH,
  ANALYSIS_MULTIVARIATE_TITLE,
  ANALYSIS_NEXT_TITLE,
  ANALYSIS_NOT_EXPLAIN_BOX_TITLE,
  ANALYSIS_OTHER_FIELDS_TITLE,
  ANALYSIS_RUN_COMPARISON_TITLE,
  ANALYSIS_SECTION_TITLE,
  ANALYSIS_TECH_DISCLAIMER,
  ANALYSIS_TECH_TITLE,
  ANALYSIS_WATERSHED_MARK,
  analysisHeroCaption,
  analysisHeroTitle,
  analysisNextSteps,
  analysisEmptyCaptureDetail,
  analysisEmptySampleDetail,
} from '../reportSectionMeta';
import {
  buildHeroRoiOption,
  buildRoiBarOption,
  correlationDirection,
  formatCount,
  formatNum,
  formatPValue,
  formatPlain,
  highlightCardsFromTiers,
  maxAbs,
  multivariateKindLabel,
  rankFillPct,
  rowsExtent,
  sameBinning,
  sampleSizeFromFacts,
  splitValueFromTiers,
  stripCornerQuotes,
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

function HighlightCard({ value, caption, tone = 'info' }) {
  return (
    <Box className={`ntq-analysis-highlight ntq-analysis-highlight--${tone || 'info'}`}>
      <Typography className="ntq-analysis-highlight__value">{value}</Typography>
      <Typography variant="caption" color="text.secondary" className="ntq-analysis-highlight__caption">
        {caption}
      </Typography>
    </Box>
  );
}

HighlightCard.propTypes = {
  value: PropTypes.string.isRequired,
  caption: PropTypes.string.isRequired,
  tone: PropTypes.string,
};

function CalloutList({ title, items = [], tone = 'ok' }) {
  const rows = Array.isArray(items) ? items.map((item) => String(item || '').trim()).filter(Boolean) : [];
  if (!rows.length) return null;
  return (
    <Box className={`ntq-analysis-callout ntq-analysis-callout--${tone || 'ok'}`}>
      <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.75 }}>{title}</Typography>
      <Stack spacing={0.5}>
        {rows.map((line) => (
          <Box key={line} className="ntq-analysis-callout__row">
            <span className="ntq-analysis-callout__mark">{tone === 'warn' ? '✕' : '✓'}</span>
            <Typography variant="body2">{line}</Typography>
          </Box>
        ))}
      </Stack>
    </Box>
  );
}

CalloutList.propTypes = {
  title: PropTypes.string.isRequired,
  items: PropTypes.arrayOf(PropTypes.string),
  tone: PropTypes.string,
};

function NumberedSteps({ items = [] }) {
  const rows = Array.isArray(items) ? items.map((item) => String(item || '').trim()).filter(Boolean) : [];
  if (!rows.length) return null;
  return (
    <Stack spacing={0.85} className="ntq-analysis-steps">
      {rows.map((line, idx) => (
        <Box key={line} className="ntq-analysis-step">
          <span className="ntq-analysis-step__n">{idx + 1}</span>
          <Typography variant="body2">{line}</Typography>
        </Box>
      ))}
    </Stack>
  );
}

NumberedSteps.propTypes = {
  items: PropTypes.arrayOf(PropTypes.string),
};

function ReadNote({ title, text = '', tip = '' }) {
  if (!text) return null;
  return (
    <Box className="ntq-analysis-read">
      <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
        <Typography className="ntq-analysis-read__title">{title}</Typography>
        {tip ? <NtqHelpTooltip title={tip} /> : null}
      </Stack>
      <Typography variant="body2">{text}</Typography>
    </Box>
  );
}

ReadNote.propTypes = {
  title: PropTypes.string.isRequired,
  text: PropTypes.string,
  tip: PropTypes.string,
};

function EmptyCheckCard({ question, detail, isHit = false }) {
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

function EmptyChecks({ reason = null }) {
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

function StepAnalysisInsights({ status, analysis = null, error = '' }) {
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
  const tiers = useMemo(
    () => (Array.isArray(facts?.tiers) ? facts.tiers.filter((t) => t && typeof t === 'object') : []),
    [facts],
  );
  const buckets = useMemo(
    () => (Array.isArray(facts?.buckets) ? facts.buckets.filter((t) => t && typeof t === 'object') : []),
    [facts],
  );
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
  const isEmpty = facts?.status === 'empty';
  const watershedDistinct = tiers.length > 0 && !sameBinning(tiers, buckets);
  const heroRows = watershedDistinct || tiers.length === 2 ? tiers : buckets;
  const heroOption = useMemo(
    () => (heroRows.length > 0
      ? buildHeroRoiOption(heroRows, {
        watershedLabel: heroRows.length === 2 ? ANALYSIS_WATERSHED_MARK : '',
      })
      : null),
    [heroRows],
  );
  const binsOption = useMemo(
    () => (watershedDistinct && buckets.length > 0
      ? buildRoiBarOption(buckets, { barMaxWidth: buckets.length > 4 ? 22 : 36, rotate: buckets.length > 4 ? 20 : 0 })
      : null),
    [watershedDistinct, buckets],
  );
  const highlights = useMemo(
    () => highlightCardsFromTiers({ tiers, buckets }),
    [tiers, buckets],
  );
  const extent = rowsExtent(heroRows.length ? heroRows : buckets);
  const heroCaption = analysisHeroCaption({
    sampleSize,
    fieldKey: facts?.field_key,
    extent,
  });
  const nextSteps = !isEmpty
    ? analysisNextSteps({
      fieldKey: facts?.field_key,
      splitValue: splitValueFromTiers(tiers),
      hasOtherFields: otherFields.length > 0,
    })
    : [];
  const techLine1 = [
    sampleSize != null ? `样本 ${formatCount(sampleSize)} 笔` : '',
    extent.min != null && extent.max != null
      ? `${facts?.field_key || '条件'} 区间 [${formatNum(extent.min, 1)}, ${formatNum(extent.max, 1)}]`
      : '',
    watershedDistinct
      ? `分档方式：按收益落差合成分水岭（细档 ${buckets.length}）`
      : (buckets.length ? `分档方式：${buckets.length} 个等频档` : ''),
  ].filter(Boolean).join(' · ');
  const techLine2 = [
    corr?.status === 'ok' && corr?.p_value != null ? `p-value：${formatPValue(corr.p_value)}` : '',
    corr?.status === 'ok' && corr?.rho != null ? `ρ=${formatNum(corr.rho, 3)}` : '',
    skipped > 0 ? `跳过 ${formatCount(skipped)} / ${formatCount(skip.investment_count)}` : '',
  ].filter(Boolean).join(' · ');
  const showMultivariate = (multivariate?.status === 'ok' || multivariate?.status === 'partial')
    && mvRanking.length > 0;
  const showCompare = runComparison?.status === 'ok' && settingsDiff.length > 0;
  const explains = (Array.isArray(conclusion?.explains) ? conclusion.explains : [])
    .map((line) => stripCornerQuotes(line))
    .filter(Boolean);
  const doesNot = (Array.isArray(conclusion?.does_not_explain) ? conclusion.does_not_explain : [])
    .map((line) => stripCornerQuotes(line))
    .filter(Boolean);
  const headline = stripCornerQuotes(conclusion?.headline || '');

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
          {isEmpty ? (
            <EmptyChecks reason={facts.empty_reason} />
          ) : (
            <>
          {highlights.length > 0 ? (
            <Stack spacing={1}>
              <SectionTitle title={ANALYSIS_FINDINGS_TITLE} tip={ANALYSIS_SECTION_TIPS.findings} />
              <Box className="ntq-analysis-highlights">
                {highlights.map((card) => (
                  <HighlightCard
                    key={card.key}
                    value={card.value}
                    caption={card.caption}
                    tone={card.tone}
                  />
                ))}
              </Box>
            </Stack>
          ) : null}

          {heroOption || headline ? (
            <SectionBlock title={analysisHeroTitle(facts.field_key)} tip={ANALYSIS_SECTION_TIPS.hero}>
              <Stack spacing={1}>
                {heroCaption ? (
                  <Typography variant="caption" color="text.secondary" className="ntq-analysis-hero-caption">
                    {heroCaption}
                  </Typography>
                ) : null}
                <ReadNote
                  title={ANALYSIS_HERO_READ_TITLE}
                  text={headline}
                  tip={ANALYSIS_SECTION_TIPS.read}
                />
                {heroOption ? (
                  <ChartPanel
                    option={heroOption}
                    height={heroRows.length <= 2 ? 220 : 200}
                    framed={false}
                  />
                ) : null}
                {binsOption ? (
                  <ChartPanel
                    title={ANALYSIS_BINS_TITLE}
                    tip={ANALYSIS_CHART_TIPS.bins}
                    option={binsOption}
                    height={buckets.length > 4 ? 200 : 180}
                    framed={false}
                  />
                ) : null}
              </Stack>
            </SectionBlock>
          ) : null}

          {explains.length > 0 || doesNot.length > 0 ? (
            <Box
              className={`ntq-analysis-split${explains.length && doesNot.length ? '' : ' ntq-analysis-split--single'}`}
            >
              <CalloutList title={ANALYSIS_EXPLAIN_BOX_TITLE} items={explains} tone="ok" />
              <CalloutList title={ANALYSIS_NOT_EXPLAIN_BOX_TITLE} items={doesNot} tone="warn" />
            </Box>
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

          {nextSteps.length > 0 ? (
            <SectionBlock title={ANALYSIS_NEXT_TITLE} tip={ANALYSIS_SECTION_TIPS.next}>
              <NumberedSteps items={nextSteps} />
            </SectionBlock>
          ) : null}

          {techLine1 || techLine2 ? (
            <SectionBlock title={ANALYSIS_TECH_TITLE} tip={ANALYSIS_SECTION_TIPS.tech}>
              <Box className="ntq-analysis-tech">
                {techLine1 ? (
                  <Typography className="ntq-analysis-tech__line">{techLine1}</Typography>
                ) : null}
                {techLine2 ? (
                  <Typography className="ntq-analysis-tech__line">{techLine2}</Typography>
                ) : null}
                <Typography className="ntq-analysis-tech__line">
                  {`免责：${ANALYSIS_TECH_DISCLAIMER}`}
                </Typography>
              </Box>
            </SectionBlock>
          ) : null}
            </>
          )}
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

export default StepAnalysisInsights;
