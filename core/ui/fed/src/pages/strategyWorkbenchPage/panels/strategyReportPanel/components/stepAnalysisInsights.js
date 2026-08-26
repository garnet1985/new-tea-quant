import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from '@mui/material';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import { ANALYSIS_SECTION_TITLE } from '../reportSectionMeta';

function formatRoiPct(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function normalizeFindingLine(item) {
  if (item == null) return '';
  if (typeof item === 'string') return item.trim();
  if (typeof item === 'object') {
    const caption = String(item.caption || '').trim();
    const value = String(item.value || '').trim();
    if (caption && value) return `${caption}：${value}`;
    return caption || value;
  }
  return String(item).trim();
}

function bulletList(items, { dense = false } = {}) {
  const rows = Array.isArray(items)
    ? items.map(normalizeFindingLine).filter(Boolean)
    : [];
  if (rows.length === 0) return null;
  return (
    <List dense={dense} disablePadding sx={{ pl: 0.5 }}>
      {rows.map((line) => (
        <ListItem key={line} disableGutters sx={{ py: 0.25, alignItems: 'flex-start' }}>
          <ListItemText
            primary={`· ${line}`}
            primaryTypographyProps={{ variant: 'body2', color: 'text.primary' }}
          />
        </ListItem>
      ))}
    </List>
  );
}

function StepAnalysisInsights({ status, analysis, error = '' }) {
  const insights = useMemo(() => {
    if (!analysis?.available || !analysis?.insights || typeof analysis.insights !== 'object') {
      return null;
    }
    return analysis.insights;
  }, [analysis]);

  if (status === 'idle') return null;

  return (
    <Box className="ntq-step-analysis">
      <Typography variant="subtitle2" fontWeight={600} className="ntq-step-analysis__title">
        {ANALYSIS_SECTION_TITLE}
      </Typography>
      {status === 'loading' ? (
        <InlineLoadingState compact block message="正在加载归因解读…" />
      ) : null}
      {status === 'error' ? (
        <Typography variant="body2" color="error" sx={{ py: 0.5 }}>
          {error || '归因解读加载失败'}
        </Typography>
      ) : null}
      {status === 'missing' ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 0.5 }}>
          本步尚未生成归因报告。若刚跑完其它步（enum 为 cache 复用），请再跑一次本步或任意一步以自动补全；也可在 CLI 执行 sa。
        </Typography>
      ) : null}
      {status === 'ok' && insights ? (
        <Stack spacing={1.25} className="ntq-step-analysis__body">
          {insights.headline ? (
            <Typography variant="body2" color="text.primary" sx={{ fontWeight: 500 }}>
              {insights.headline}
            </Typography>
          ) : null}
          {insights.chart_note ? (
            <Typography variant="body2" color="text.secondary">
              {insights.chart_note}
            </Typography>
          ) : null}
          {Array.isArray(insights.tiers) && insights.tiers.length > 0 ? (
            <Stack spacing={0.5}>
              <Typography variant="caption" color="text.secondary">
                分档平均收益
              </Typography>
              {insights.tiers.map((tier) => {
                if (!tier || typeof tier !== 'object') return null;
                const label = String(tier.label || '?').trim();
                const roi = formatRoiPct(tier.mean_roi);
                const count = tier.count != null ? ` · n=${tier.count}` : '';
                return (
                  <Typography key={label} variant="body2" color="text.primary">
                    {`${label}：${roi}${count}`}
                  </Typography>
                );
              })}
            </Stack>
          ) : null}
          {bulletList(insights.key_findings)}
          {insights.multivariate?.status === 'ok' && insights.multivariate?.headline ? (
            <Typography variant="body2" color="text.primary">
              {`多指标一起看：${insights.multivariate.headline}`}
            </Typography>
          ) : null}
          {insights.run_comparison?.status === 'ok' && insights.run_comparison?.headline ? (
            <Typography variant="body2" color="text.primary">
              {`版本对照：${insights.run_comparison.headline}`}
            </Typography>
          ) : null}
          {bulletList(insights.explains, { dense: true })}
          {bulletList(insights.does_not_explain, { dense: true })}
          {bulletList(insights.next_steps, { dense: true })}
        </Stack>
      ) : null}
      {status === 'ok' && !insights ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 0.5 }}>
          归因报告为空或尚未生成有效结论。
        </Typography>
      ) : null}
    </Box>
  );
}

StepAnalysisInsights.propTypes = {
  status: PropTypes.oneOf(['idle', 'loading', 'ok', 'missing', 'error']).isRequired,
  analysis: PropTypes.shape({
    available: PropTypes.bool,
    insights: PropTypes.object,
  }),
  error: PropTypes.string,
};

StepAnalysisInsights.defaultProps = {
  analysis: null,
  error: '',
};

export default StepAnalysisInsights;
