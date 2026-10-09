import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Alert,
  Box,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import './style.scss';

const LAYERS = [
  {
    key: 'enum',
    title: '枚举',
    columns: [
      ['total_opportunities', '机会数', 'count', true],
      ['trigger_stocks', '触发股票数', 'count', true],
      ['cv', '时间分散', 'number', true],
    ],
  },
  {
    key: 'price',
    title: '价格',
    columns: [
      ['win_rate', '胜率', 'percent', true],
      ['avg_roi', '平均收益率', 'ratio', true],
      ['top5_trade_profit_share', '前5笔利润占比', 'ratio', true],
    ],
  },
  {
    key: 'portfolio',
    title: '资金',
    columns: [
      ['max_drawdown', '最大回撤', 'ratio', true],
      ['sharpe_ratio', '夏普', 'number', true],
      ['sortino_ratio', 'Sortino', 'number', true],
      ['calmar_ratio', 'Calmar', 'number', true],
      ['total_return', '账户收益', 'ratio', false],
    ],
  },
];

function formatNumber(value, style, signed = false) {
  if (value == null || value === '') return '—';
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  const sign = signed && number > 0 ? '+' : '';
  if (style === 'count') {
    const shown = String(Math.round(number));
    return signed ? `${sign}${shown}` : shown;
  }
  if (style === 'ratio') return `${sign}${(number * 100).toFixed(1)}%`;
  if (style === 'percent') return `${sign}${number.toFixed(1)}%`;
  return `${sign}${number.toFixed(2)}`;
}

function formatCell(cell, style, includeDelta) {
  if (!cell || typeof cell !== 'object') return '—';
  const value = formatNumber(cell.value, style);
  if (!includeDelta || cell.delta == null) return value;
  return `${value} (${formatNumber(cell.delta, style, true)})`;
}

function formatDays(value) {
  if (value == null || value === '') return '—';
  const number = Number(value);
  return Number.isFinite(number) ? String(Math.round(number)) : '—';
}

function reportRows(payload) {
  const baseline = payload?.baseline && typeof payload.baseline === 'object'
    ? { ...payload.baseline, is_baseline: true }
    : null;
  const windows = Array.isArray(payload?.windows) ? payload.windows : [];
  return baseline ? [baseline, ...windows] : windows;
}

function MetricTable({ title, columns, rows }) {
  return (
    <Box className="ntq-design-roll-report__block">
      <Typography variant="subtitle2" className="ntq-design-roll-report__title">
        {title}
      </Typography>
      <Box className="ntq-design-roll-report__table-wrap">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>窗口</TableCell>
              {columns.map(([, label]) => (
                <TableCell key={label} align="right">{label}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow
                key={`${row.version_id || ''}-${row.label || ''}`}
                className={row.is_baseline ? 'ntq-design-roll-report__row--baseline' : undefined}
              >
                <TableCell>{row.label || '—'}</TableCell>
                {columns.map(([key, , style, includeDelta]) => {
                  const cell = rowLayer(row, columns)?.[key];
                  return (
                    <TableCell key={key} align="right">
                      {formatCell(cell, style, includeDelta && !row.is_baseline)}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}

function rowLayer(row, columns) {
  const layer = LAYERS.find((item) => item.columns === columns);
  const layers = row?.layers && typeof row.layers === 'object' ? row.layers : {};
  return layer ? layers[layer.key] || {} : {};
}

MetricTable.propTypes = {
  title: PropTypes.string.isRequired,
  columns: PropTypes.array.isRequired,
  rows: PropTypes.array.isRequired,
};

/**
 * 滚动对照报告：基准行在前，后面是各窗口相对基准的差值。
 */
function StrategyDesignRollingReport({
  payload = null,
  loading = false,
  error = '',
  busy = false,
}) {
  const rows = useMemo(() => reportRows(payload), [payload]);
  const baseline = payload?.baseline && typeof payload.baseline === 'object'
    ? payload.baseline
    : null;

  if (loading) {
    return (
      <Box className="ntq-design-roll-report ntq-design-roll-report--center">
        <CircularProgress size={28} />
        <Typography variant="body2" color="text.secondary">正在读取滚动报告…</Typography>
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!rows.length) {
    return (
      <Box className="ntq-design-roll-report ntq-design-roll-report--empty">
        <Typography variant="body2" color="text.secondary">
          {busy
            ? '滚动对照进行中，完成后会显示在这里。'
            : '尚未运行滚动测试。配置 rolling.py 后，在投资组合面板点击「滚动测试」。'}
        </Typography>
      </Box>
    );
  }

  const notes = rows
    .map((row) => {
      const text = String(row.dispersion_conclusion || '').trim();
      if (!text) return null;
      return `${row.label || '窗口'} 时间分散：${text}`;
    })
    .filter(Boolean);

  return (
    <Box className="ntq-design-roll-report">
      <Typography variant="caption" color="text.secondary" className="ntq-design-roll-report__meta">
        {`主版本 ${payload?.parent_version_id || baseline?.version_id || '—'} · 基准 ${baseline?.start || '—'}-${baseline?.end || '—'} · ${rows.length - (rows[0]?.is_baseline ? 1 : 0)} 段窗口`}
      </Typography>
      <Box className="ntq-design-roll-report__table-wrap">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>窗口</TableCell>
              <TableCell>版本</TableCell>
              <TableCell align="right">长度（天）</TableCell>
              <TableCell align="right">与基准重叠（天）</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow
                key={`span-${row.version_id || ''}-${row.label || ''}`}
                className={row.is_baseline ? 'ntq-design-roll-report__row--baseline' : undefined}
              >
                <TableCell>{row.label || '—'}</TableCell>
                <TableCell>{row.version_id || '—'}</TableCell>
                <TableCell align="right">{formatDays(row.length_days)}</TableCell>
                <TableCell align="right">
                  {row.is_baseline ? '—' : formatDays(row.overlap_days)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
      {LAYERS.map((layer) => (
        <MetricTable
          key={layer.key}
          title={layer.title}
          columns={layer.columns}
          rows={rows}
        />
      ))}
      {notes.length ? (
        <Box className="ntq-design-roll-report__notes">
          {notes.map((line) => (
            <Typography key={line} variant="caption" color="text.secondary">
              {line}
            </Typography>
          ))}
        </Box>
      ) : null}
    </Box>
  );
}

StrategyDesignRollingReport.propTypes = {
  payload: PropTypes.object,
  loading: PropTypes.bool,
  error: PropTypes.string,
  busy: PropTypes.bool,
};

export default StrategyDesignRollingReport;
