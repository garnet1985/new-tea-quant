import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import {
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
import './strategyDesignAttributeReport.scss';

function asList(value) {
  return Array.isArray(value) ? value : [];
}

function nestedReport(payload) {
  const report = payload?.report;
  if (report && typeof report === 'object') {
    const inner = report.report;
    if (inner && typeof inner === 'object') return inner;
    return report;
  }
  return {};
}

function flattenTable(table) {
  if (Array.isArray(table)) return table;
  if (table && typeof table === 'object') {
    return Object.values(table).flatMap((part) => (Array.isArray(part) ? part : []));
  }
  return [];
}

function formatCell(value) {
  if (value == null || value === '') return '—';
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.abs(value) >= 100 || Number.isInteger(value)
      ? String(value)
      : value.toFixed(3);
  }
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

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
  const headline = String(payload?.headline || summary.headline || '').trim();
  const highlights = asList(summary.highlights);
  const hints = asList(summary.hints).map((item) => String(item || '').trim()).filter(Boolean);
  const rows = useMemo(() => flattenTable(payload?.table).slice(0, 40), [payload]);

  const columns = useMemo(() => {
    if (!rows.length) return [];
    const preferred = ['version_id', 'family', 'status', 'outcome', 'roi', 'win_rate'];
    const keys = new Set();
    rows.forEach((row) => {
      if (row && typeof row === 'object') {
        Object.keys(row).forEach((key) => {
          if (key === 'overlay' || key === 'execute_settings') return;
          keys.add(key);
        });
      }
    });
    const ordered = preferred.filter((key) => keys.has(key));
    const rest = [...keys].filter((key) => !preferred.includes(key)).slice(0, 6);
    return [...ordered, ...rest].slice(0, 8);
  }, [rows]);

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
      {headline ? (
        <Typography variant="subtitle1" className="ntq-design-attr-report__headline">
          {headline}
        </Typography>
      ) : null}

      {hints.length ? (
        <Stack spacing={0.5} className="ntq-design-attr-report__hints">
          {hints.map((hint) => (
            <Typography key={hint} variant="caption" color="text.secondary">
              {hint}
            </Typography>
          ))}
        </Stack>
      ) : null}

      {highlights.length ? (
        <Box className="ntq-design-attr-report__section">
          <Typography variant="subtitle2" className="ntq-design-attr-report__section-title">
            主要相关
          </Typography>
          <Stack spacing={0.75} component="ul" className="ntq-design-attr-report__list">
            {highlights.map((item, idx) => {
              const knob = String(item?.knob || '').trim() || '参数';
              const outcome = String(item?.outcome || '').trim() || '结果';
              const rho = Number(item?.rho);
              const rhoText = Number.isFinite(rho) ? `ρ=${rho.toFixed(3)}` : '';
              return (
                <Typography
                  key={`${knob}-${outcome}-${idx}`}
                  component="li"
                  variant="body2"
                  className="ntq-design-attr-report__list-item"
                >
                  {knob}
                  {' · '}
                  {outcome}
                  {rhoText ? ` · ${rhoText}` : ''}
                </Typography>
              );
            })}
          </Stack>
        </Box>
      ) : null}

      {rows.length && columns.length ? (
        <Box className="ntq-design-attr-report__section">
          <Typography variant="subtitle2" className="ntq-design-attr-report__section-title">
            对照表
          </Typography>
          <Box className="ntq-design-attr-report__table-wrap">
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {columns.map((col) => (
                    <TableCell key={col}>{col}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row, idx) => (
                  <TableRow key={String(row?.version_id || idx)}>
                    {columns.map((col) => (
                      <TableCell key={col}>{formatCell(row?.[col])}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Box>
      ) : null}

      {!headline && !highlights.length && !rows.length ? (
        <Typography variant="body2" color="text.secondary">
          已有归因产物，但没有可展示的摘要字段。
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
