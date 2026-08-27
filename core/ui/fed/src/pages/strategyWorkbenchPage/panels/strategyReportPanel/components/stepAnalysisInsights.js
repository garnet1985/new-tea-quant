import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Stack,
  Typography,
} from '@mui/material';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import {
  ANALYSIS_CORRELATION_CAPTION,
  ANALYSIS_EMPTY_ZH,
  ANALYSIS_ERROR_ZH,
  ANALYSIS_LOADING_ZH,
  ANALYSIS_MISSING_ZH,
  ANALYSIS_MULTIVARIATE_CAPTION,
  ANALYSIS_OTHER_FIELDS_CAPTION,
  ANALYSIS_PRIMARY_FIELD_CAPTION,
  ANALYSIS_RUN_COMPARISON_CAPTION,
  ANALYSIS_SECTION_TITLE,
  ANALYSIS_SKIP_CAPTION,
  ANALYSIS_TIERS_CAPTION,
} from '../reportSectionMeta';

function formatRoiPct(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatNum(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Number(value).toFixed(digits);
}

function formatPValue(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  if (n === 0) return '0';
  if (n < 0.001) return n.toExponential(1);
  return n.toFixed(3);
}

function formatPlain(value) {
  if (value == null) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function captionBlock(caption, children) {
  if (!children) return null;
  return (
    <Stack spacing={0.5}>
      <Typography variant="caption" color="text.secondary">
        {caption}
      </Typography>
      {children}
    </Stack>
  );
}

function StepAnalysisInsights({ status, analysis, error = '' }) {
  const facts = useMemo(() => {
    if (!analysis?.enabled || !analysis?.facts || typeof analysis.facts !== 'object') {
      return null;
    }
    return analysis.facts;
  }, [analysis]);

  if (status === 'idle') return null;
  if (analysis && analysis.enabled === false) return null;

  const skip = facts?.skip_summary && typeof facts.skip_summary === 'object'
    ? facts.skip_summary
    : null;
  const corr = facts?.correlation && typeof facts.correlation === 'object'
    ? facts.correlation
    : null;
  const tiers = Array.isArray(facts?.tiers) ? facts.tiers : [];
  const otherFields = Array.isArray(facts?.other_fields) ? facts.other_fields : [];
  const multivariate = facts?.multivariate && typeof facts.multivariate === 'object'
    ? facts.multivariate
    : null;
  const runComparison = facts?.run_comparison && typeof facts.run_comparison === 'object'
    ? facts.run_comparison
    : null;
  const settingsDiff = Array.isArray(runComparison?.settings_diff)
    ? runComparison.settings_diff
    : [];

  return (
    <Box className="ntq-step-analysis">
      <Typography variant="subtitle2" fontWeight={600} className="ntq-step-analysis__title">
        {ANALYSIS_SECTION_TITLE}
      </Typography>
      {status === 'loading' ? (
        <InlineLoadingState compact block message={ANALYSIS_LOADING_ZH} />
      ) : null}
      {status === 'error' ? (
        <Typography variant="body2" color="error" sx={{ py: 0.5 }}>
          {error || ANALYSIS_ERROR_ZH}
        </Typography>
      ) : null}
      {status === 'missing' ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 0.5 }}>
          {ANALYSIS_MISSING_ZH}
        </Typography>
      ) : null}
      {status === 'ok' && facts ? (
        <Stack spacing={1.25} className="ntq-step-analysis__body">
          {facts.status === 'empty' ? (
            <Typography variant="body2" color="text.secondary">
              {ANALYSIS_EMPTY_ZH}
            </Typography>
          ) : null}
          {facts.field_key ? (
            captionBlock(
              ANALYSIS_PRIMARY_FIELD_CAPTION,
              <Typography variant="body2" color="text.primary">
                {String(facts.field_key)}
              </Typography>,
            )
          ) : null}
          {corr && corr.status === 'ok' ? (
            captionBlock(
              ANALYSIS_CORRELATION_CAPTION,
              <Typography variant="body2" color="text.primary">
                {`ρ=${formatNum(corr.rho, 3)} · p=${formatPValue(corr.p_value)}`}
              </Typography>,
            )
          ) : null}
          {tiers.length > 0 ? (
            captionBlock(
              ANALYSIS_TIERS_CAPTION,
              tiers.map((tier) => {
                if (!tier || typeof tier !== 'object') return null;
                const label = String(tier.label || '?').trim();
                const roi = formatRoiPct(tier.mean_roi);
                const count = tier.count != null ? ` · n=${tier.count}` : '';
                return (
                  <Typography key={label} variant="body2" color="text.primary">
                    {`${label}：${roi}${count}`}
                  </Typography>
                );
              }),
            )
          ) : null}
          {skip && Number(skip.skipped_count) > 0 ? (
            captionBlock(
              ANALYSIS_SKIP_CAPTION,
              <Typography variant="body2" color="text.primary">
                {`${Number(skip.skipped_count) || 0} / ${Number(skip.investment_count) || 0}`}
              </Typography>,
            )
          ) : null}
          {otherFields.length > 0 ? (
            captionBlock(
              ANALYSIS_OTHER_FIELDS_CAPTION,
              otherFields.map((row) => {
                if (!row || typeof row !== 'object') return null;
                const key = String(row.key || '?');
                return (
                  <Typography key={key} variant="body2" color="text.primary">
                    {`${key} · ρ=${formatNum(row.rho, 2)}`}
                  </Typography>
                );
              }),
            )
          ) : null}
          {multivariate && (multivariate.status === 'ok' || multivariate.status === 'partial')
            && Array.isArray(multivariate.ranking) && multivariate.ranking.length > 0 ? (
            captionBlock(
              ANALYSIS_MULTIVARIATE_CAPTION,
              multivariate.ranking.map((row) => {
                if (!row || typeof row !== 'object') return null;
                const key = String(row.key || '?');
                return (
                  <Typography key={key} variant="body2" color="text.primary">
                    {`${key} · ${formatNum(row.coef, 3)}`}
                  </Typography>
                );
              }),
            )
          ) : null}
          {runComparison?.status === 'ok' && settingsDiff.length > 0 ? (
            captionBlock(
              ANALYSIS_RUN_COMPARISON_CAPTION,
              settingsDiff.map((row) => {
                if (!row || typeof row !== 'object') return null;
                const key = String(row.key || '?');
                return (
                  <Typography key={key} variant="body2" color="text.primary">
                    {`${key}：${formatPlain(row.baseline)} → ${formatPlain(row.current)}`}
                  </Typography>
                );
              }),
            )
          ) : null}
        </Stack>
      ) : null}
      {status === 'ok' && !facts ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 0.5 }}>
          {ANALYSIS_EMPTY_ZH}
        </Typography>
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
  }),
  error: PropTypes.string,
};

StepAnalysisInsights.defaultProps = {
  analysis: null,
  error: '',
};

export default StepAnalysisInsights;
