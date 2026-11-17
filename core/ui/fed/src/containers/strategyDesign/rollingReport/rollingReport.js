import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { Loading, Message } from 'ui';
import './style.scss';

const LAYERS = [
  {
    key: 'enum',
    title: '机会盘点',
    columns: [
      { key: 'total_opportunities', label: '机会数', style: 'count', delta: true },
      { key: 'trigger_stocks', label: '触发股票数', style: 'count', delta: true },
      { key: 'cv', label: '时间分散', style: 'number', delta: true },
    ],
  },
  {
    key: 'price',
    title: '价格',
    columns: [
      { key: 'win_rate', label: '胜率', style: 'percent', delta: true },
      { key: 'avg_roi', label: '平均收益率', style: 'ratio', delta: true },
      { key: 'top5_trade_profit_share', label: '前5笔利润占比', style: 'ratio', delta: true },
    ],
  },
  {
    key: 'portfolio',
    title: '资金',
    columns: [
      { key: 'max_drawdown', label: '最大回撤', style: 'ratio', delta: true },
      { key: 'sharpe_ratio', label: '夏普', style: 'number', delta: true },
      { key: 'sortino_ratio', label: 'Sortino', style: 'number', delta: true },
      { key: 'calmar_ratio', label: 'Calmar', style: 'number', delta: true },
      { key: 'total_return', label: '账户收益', style: 'ratio', delta: false },
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

function layerCells(row, layerKey) {
  const layers = row?.layers && typeof row.layers === 'object' ? row.layers : {};
  const block = layers[layerKey];
  return block && typeof block === 'object' ? block : {};
}

function MetricTable({ title, layerKey, columns, rows }) {
  return (
    <div className="ntq-design-roll-report__block">
      <h3 className="ntq-design-roll-report__title">{title}</h3>
      <div className="ntq-design-roll-report__table-wrap">
        <table className="ntq-design-roll-report__table">
          <thead>
            <tr>
              <th>窗口</th>
              {columns.map((column) => (
                <th key={column.key} className="is-num">{column.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const cells = layerCells(row, layerKey);
              return (
                <tr
                  key={`${layerKey}-${row.version_id || ''}-${row.label || ''}`}
                  className={row.is_baseline ? 'ntq-design-roll-report__row--baseline' : undefined}
                >
                  <td>{row.label || '—'}</td>
                  {columns.map((column) => (
                    <td key={column.key} className="is-num">
                      {formatCell(
                        cells[column.key],
                        column.style,
                        column.delta && !row.is_baseline,
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

MetricTable.propTypes = {
  title: PropTypes.string.isRequired,
  layerKey: PropTypes.string.isRequired,
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
      <div className="ntq-design-roll-report ntq-design-roll-report--center">
        <Loading variant="inline" aria-label="正在读取滚动报告" />
        <p className="ntq-muted">正在读取滚动报告…</p>
      </div>
    );
  }

  if (error) {
    return <Message status="error">{error}</Message>;
  }

  if (!rows.length) {
    return (
      <div className="ntq-design-roll-report ntq-design-roll-report--empty">
        <p className="ntq-muted">
          {busy
            ? '滚动对照进行中，完成后会显示在这里。'
            : '尚未运行滚动测试。配置 rolling.py 后，在投资组合面板点击「滚动测试」。'}
        </p>
      </div>
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
    <div className="ntq-design-roll-report">
      <p className="ntq-design-roll-report__meta ntq-muted">
        {`主版本 ${payload?.parent_version_id || baseline?.version_id || '—'} · 基准 ${baseline?.start || '—'}-${baseline?.end || '—'} · ${rows.length - (rows[0]?.is_baseline ? 1 : 0)} 段窗口`}
      </p>
      <div className="ntq-design-roll-report__table-wrap">
        <table className="ntq-design-roll-report__table">
          <thead>
            <tr>
              <th>窗口</th>
              <th>版本</th>
              <th className="is-num">长度（天）</th>
              <th className="is-num">与基准重叠（天）</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={`span-${row.version_id || ''}-${row.label || ''}`}
                className={row.is_baseline ? 'ntq-design-roll-report__row--baseline' : undefined}
              >
                <td>{row.label || '—'}</td>
                <td>{row.version_id || '—'}</td>
                <td className="is-num">{formatDays(row.length_days)}</td>
                <td className="is-num">
                  {row.is_baseline ? '—' : formatDays(row.overlap_days)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {LAYERS.map((layer) => (
        <MetricTable
          key={layer.key}
          title={layer.title}
          layerKey={layer.key}
          columns={layer.columns}
          rows={rows}
        />
      ))}
      {notes.length ? (
        <div className="ntq-design-roll-report__notes">
          {notes.map((line) => (
            <p key={line} className="ntq-caption ntq-muted">{line}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

StrategyDesignRollingReport.propTypes = {
  payload: PropTypes.object,
  loading: PropTypes.bool,
  error: PropTypes.string,
  busy: PropTypes.bool,
};

export default StrategyDesignRollingReport;
