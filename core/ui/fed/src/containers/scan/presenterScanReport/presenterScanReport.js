/**
 * SPECIAL-CASE（post_process DEC-05）：写死消费 ``view=presenter`` 的 scan_report UI。
 * 第二个会改前端渲染的 adapter 出现时，改为契约 + 解析引擎，废掉本分支。
 */
import React, { useMemo } from 'react';
import {
  Box,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import './presenterScanReport.scss';

function formatPct(raw, { assumeFraction = true } = {}) {
  const n = Number(raw);
  if (!Number.isFinite(n)) return '—';
  let pct = n;
  if (assumeFraction && Math.abs(n) <= 1) pct = n * 100;
  return `${pct.toFixed(1)}%`;
}

function formatPrice(raw) {
  const n = Number(raw);
  if (!Number.isFinite(n)) return raw == null || raw === '' ? '—' : String(raw);
  return n.toFixed(2);
}

function formatScanDate(v) {
  const raw = String(v || '').trim();
  if (!raw) return '—';
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  if (/^\d{8}$/.test(raw)) return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
  return raw;
}

function sessionSummaryLine(summary) {
  if (!summary || typeof summary !== 'object') return null;
  // overall_report 可能整包下发，指标在嵌套 summary
  const s = (summary.summary && typeof summary.summary === 'object')
    ? summary.summary
    : summary;
  const total = s.total_investments ?? s.totalInvestments;
  const winRate = s.win_rate ?? s.winRate;
  const avgRoi = s.avg_roi ?? s.avg_return ?? s.avgReturn;
  if (total == null && winRate == null && avgRoi == null) return null;
  // price overall_report.win_rate 常为百分数（如 58.7）；by_stock 为 0~1
  const winLooksPercent = Number(winRate) > 1;
  return {
    total: total == null ? '—' : String(total),
    winRate: formatPct(winRate, { assumeFraction: !winLooksPercent }),
    avgRoi: formatPct(avgRoi, { assumeFraction: true }),
  };
}

/**
 * @param {object} props
 * @param {object} [props.ui] ``post_process.ui.scan_report``（含 view / props）
 * @param {string} [props.fallbackStrategyName]
 * @param {'panel'|'dialog'} [props.variant]
 */
function PresenterScanReport({
  ui,
  fallbackStrategyName = '',
  variant = 'panel',
}) {
  const payload = useMemo(() => {
    const props = ui?.props && typeof ui.props === 'object' ? ui.props : {};
    return props;
  }, [ui]);

  const strategies = Array.isArray(payload.strategies) ? payload.strategies : [];
  const historyByStrategy = payload.backtest_history && typeof payload.backtest_history === 'object'
    ? payload.backtest_history
    : {};

  const rootClass = [
    'presenter-scan-report',
    variant === 'dialog' ? 'presenter-scan-report--dialog' : '',
  ].filter(Boolean).join(' ');

  if (!strategies.length) {
    return (
      <Box className={rootClass}>
        <Typography variant="body2" color="text.secondary">
          暂无策略会话数据。
        </Typography>
      </Box>
    );
  }

  return (
    <Box className={rootClass}>
      <Typography variant="body2" color="text.secondary" className="presenter-scan-report__meta">
        会话扫描日：{formatScanDate(payload.scan_date)}
        {payload.emitted_at ? ` · 生成 ${payload.emitted_at}` : ''}
      </Typography>

      <Stack spacing={2.5}>
        {strategies.map((row) => {
          const name = String(row?.strategy_name || fallbackStrategyName || '—');
          const opps = Array.isArray(row?.opportunities) ? row.opportunities : [];
          const hist = historyByStrategy[name] || historyByStrategy[row?.strategy_name] || {};
          const summaryLine = sessionSummaryLine(hist.session_summary);
          const byStock = hist.by_stock && typeof hist.by_stock === 'object' ? hist.by_stock : {};

          return (
            <Box key={name} className="presenter-scan-report__strategy">
              <Typography variant="subtitle1" fontWeight={700}>
                {name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                扫描日 {formatScanDate(row?.scan_date || payload.scan_date)}
                {' · '}
                机会 {opps.length}
                {row?.strategy_version ? ` · 版本 ${row.strategy_version}` : ''}
              </Typography>

              {hist.error ? (
                <Typography variant="body2" color="warning.main" className="presenter-scan-report__hist-err">
                  回测历史加载失败：{String(hist.error)}
                </Typography>
              ) : null}

              {summaryLine ? (
                <Typography variant="body2" color="text.secondary" className="presenter-scan-report__hist-summary">
                  回测整体：投资次数={summaryLine.total}
                  {' · '}
                  胜率={summaryLine.winRate}
                  {' · '}
                  平均收益={summaryLine.avgRoi}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary" className="presenter-scan-report__hist-summary">
                  回测整体：（无 price 层 overall_report / 尚未回测）
                </Typography>
              )}

              {opps.length ? (
                <Table size="small" className="presenter-scan-report__table">
                  <TableHead>
                    <TableRow>
                      <TableCell>标的</TableCell>
                      <TableCell>触发日</TableCell>
                      <TableCell align="right">触发价</TableCell>
                      <TableCell align="right">历史完成</TableCell>
                      <TableCell align="right">胜率</TableCell>
                      <TableCell align="right">平均收益</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {opps.map((opp, idx) => {
                      const entityId = String(opp?.entity_id || '').trim();
                      const label = opp?.entity_name || entityId || '—';
                      const stats = entityId && byStock[entityId] && typeof byStock[entityId] === 'object'
                        ? byStock[entityId]
                        : null;
                      return (
                        <TableRow key={String(opp?.id || `${entityId}-${idx}`)}>
                          <TableCell>
                            <Typography variant="body2" fontWeight={600}>{label}</Typography>
                            {entityId && entityId !== label ? (
                              <Typography variant="caption" color="text.secondary">{entityId}</Typography>
                            ) : null}
                          </TableCell>
                          <TableCell>{formatScanDate(opp?.trigger_date)}</TableCell>
                          <TableCell align="right">{formatPrice(opp?.trigger_price)}</TableCell>
                          <TableCell align="right">
                            {stats?.completed_investments != null
                              ? String(stats.completed_investments)
                              : '—'}
                          </TableCell>
                          <TableCell align="right">
                            {stats ? formatPct(stats.win_rate) : '—'}
                          </TableCell>
                          <TableCell align="right">
                            {stats ? formatPct(stats.avg_return) : '—'}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              ) : (
                <Typography variant="body2" color="text.secondary">（无机会）</Typography>
              )}
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}

export default PresenterScanReport;

/** @param {object|null|undefined} reportPayload */
export function readPresenterScanUi(reportPayload) {
  const slot = reportPayload?.post_process?.ui?.scan_report;
  if (!slot || typeof slot !== 'object') return null;
  // SPECIAL-CASE DEC-05：仅识别 view=presenter
  if (String(slot.view || '') !== 'presenter') return null;
  return slot;
}
