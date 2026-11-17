/**
 * SPECIAL-CASE（post_process DEC-05）：写死消费 ``view=presenter`` 的 scan_report UI。
 * 机会明细 = 邮件同款两列（股票 / 机会信息）；有 presenter 时追加回测列。
 * 第二个会改前端渲染的 adapter 出现时，改为契约 + 解析引擎，废掉本分支。
 */
import React from 'react';

/** 与 ntq_email / report_template 默认仓位一致 */
const DEFAULT_QTY = 100;

/** @param {object|null|undefined} reportPayload */
export function readPresenterScanUi(reportPayload) {
  const slot = reportPayload?.post_process?.ui?.scan_report;
  if (!slot || typeof slot !== 'object') return null;
  if (String(slot.view || '') !== 'presenter') return null;
  return slot;
}

/**
 * @param {object|null|undefined} ui
 * @param {string} [strategyName]
 */
export function readPresenterHistory(ui, strategyName = '') {
  const props = ui?.props && typeof ui.props === 'object' ? ui.props : {};
  const historyByStrategy = props.backtest_history && typeof props.backtest_history === 'object'
    ? props.backtest_history
    : {};
  const name = String(strategyName || '').trim();
  let hist = name ? historyByStrategy[name] : null;
  if (!hist || typeof hist !== 'object') {
    const strategies = Array.isArray(props.strategies) ? props.strategies : [];
    const firstName = String(strategies[0]?.strategy_name || '').trim();
    hist = (firstName && historyByStrategy[firstName])
      || Object.values(historyByStrategy)[0]
      || null;
  }
  if (!hist || typeof hist !== 'object') {
    return { byStock: {}, sessionSummary: null, error: '' };
  }
  let summary = hist.session_summary;
  // 兼容未解包的 overall_report 整包
  if (summary && typeof summary === 'object' && summary.summary && typeof summary.summary === 'object') {
    const nested = summary.summary;
    const period = summary.backtest_period;
    summary = { ...nested };
    if (period && typeof period === 'object' && !summary.backtest_period) {
      summary.backtest_period = period;
    }
  }
  return {
    byStock: hist.by_stock && typeof hist.by_stock === 'object' ? hist.by_stock : {},
    sessionSummary: summary && typeof summary === 'object' ? summary : null,
    error: hist.error ? String(hist.error) : '',
  };
}

export function formatPct(raw, { assumeFraction = true } = {}) {
  const n = Number(raw);
  if (!Number.isFinite(n)) return '—';
  let pct = n;
  if (assumeFraction && Math.abs(n) <= 1) pct = n * 100;
  return `${pct.toFixed(1)}%`;
}

export function formatPrice(raw) {
  const n = Number(raw);
  if (!Number.isFinite(n)) return raw == null || raw === '' ? '—' : String(raw);
  return n.toFixed(2);
}

export function formatQty(raw) {
  const n = Number(raw);
  if (!Number.isFinite(n)) return '—';
  return Number.isInteger(n) ? String(n) : String(n);
}

export function formatNotional(raw) {
  const n = Number(raw);
  if (!Number.isFinite(n)) return '—';
  if (Math.abs(n - Math.round(n)) < 1e-6) return String(Math.round(n));
  return n.toFixed(2);
}

export function formatScanDateLabel(v) {
  const raw = String(v || '').trim();
  if (!raw) return '—';
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  if (/^\d{8}$/.test(raw)) return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
  return raw;
}

function suggestSize(price, snapshot) {
  const snap = snapshot && typeof snapshot === 'object' ? snapshot : {};
  const qtyRaw = snap.qty ?? snap.suggested_qty ?? snap.shares ?? DEFAULT_QTY;
  const qty = Number(qtyRaw);
  const p = Number(price);
  let notional = snap.notional ?? snap.total_cost ?? snap.cost;
  if ((notional == null || notional === '') && Number.isFinite(p) && Number.isFinite(qty)) {
    notional = p * qty;
  }
  return {
    price: Number.isFinite(p) ? p : null,
    qty: Number.isFinite(qty) ? qty : null,
    notional: Number(notional),
  };
}

/**
 * @param {object} opp
 * @param {number} idx
 * @param {Record<string, object>} byStock
 */
export function mapOpportunityRow(opp, idx, byStock = {}) {
  const stockId = String(opp?.stock_id || opp?.stockId || opp?.entity_id || '').trim();
  const snap = opp?.signal_snapshot ?? opp?.signalSnapshot ?? opp?.snapshot ?? {};
  const price = opp?.trigger_price ?? opp?.triggerPrice ?? '';
  const size = suggestSize(price, snap);
  const stats = stockId && byStock[stockId] && typeof byStock[stockId] === 'object'
    ? byStock[stockId]
    : null;
  return {
    id: stockId || `${idx}`,
    stock_id: stockId,
    stock_name: String(opp?.stock_name || opp?.stockName || opp?.entity_name || ''),
    trigger_price: size.price,
    qty: size.qty,
    notional: Number.isFinite(size.notional) ? size.notional : null,
    bt_completed: stats?.completed_investments ?? null,
    bt_win_rate: stats?.win_rate ?? null,
    bt_avg_return: stats?.avg_return ?? null,
  };
}

/** 回测整体结果文案（含区间） */
export function formatSessionSummaryLine(sessionSummary) {
  if (!sessionSummary || typeof sessionSummary !== 'object') return '';
  const total = sessionSummary.total_investments ?? sessionSummary.totalInvestments;
  const winRate = sessionSummary.win_rate ?? sessionSummary.winRate;
  const avgRoi = sessionSummary.avg_roi ?? sessionSummary.avg_return ?? sessionSummary.avgReturn;
  if (total == null && winRate == null && avgRoi == null) return '';
  const winLooksPercent = Number(winRate) > 1;
  const period = sessionSummary.backtest_period || sessionSummary.backtestPeriod || {};
  const start = formatScanDateLabel(period.start_date || period.startDate || '');
  const end = formatScanDateLabel(period.end_date || period.endDate || '');
  const range = (start !== '—' && end !== '—') ? `${start} ~ ${end}` : '';
  const parts = [
    `胜率 ${formatPct(winRate, { assumeFraction: !winLooksPercent })}`,
    `次数 ${total == null ? '—' : String(total)}`,
    `平均收益 ${formatPct(avgRoi, { assumeFraction: true })}`,
  ];
  if (range) parts.push(`区间 ${range}`);
  return parts.join(' · ');
}

/**
 * 表顶摘要条：策略 / 扫描日期（青） / 总机会数；可选回测整体一行。
 */
export function OpportunityDetailMeta({
  strategyName = '',
  scanDate = '',
  opportunityCount = null,
  presenterLine = '',
  presenterError = '',
}) {
  return (
    <div className="scan-detail__meta">
      <div className="scan-detail__meta-strip">
        <div className="scan-detail__meta-cell">
          <div className="scan-detail__meta-label">策略</div>
          <div className="scan-detail__meta-value">
            {strategyName || '—'}
          </div>
        </div>
        <div className="scan-detail__meta-cell">
          <div className="scan-detail__meta-label">扫描日期</div>
          <div className="scan-detail__meta-value scan-detail__meta-value--accent">
            {formatScanDateLabel(scanDate)}
          </div>
        </div>
        <div className="scan-detail__meta-cell">
          <div className="scan-detail__meta-label">总机会数</div>
          <div className="scan-detail__meta-value scan-detail__meta-value--strong">
            {opportunityCount == null ? '—' : String(opportunityCount)}
          </div>
        </div>
      </div>
      {presenterError || presenterLine ? (
        <div className="scan-detail__bt-block">
          {presenterError ? (
            <div className="scan-detail__bt-line scan-detail__bt-line--warn">
              回测整体结果：{presenterError}
            </div>
          ) : (
            <div className="scan-detail__bt-line">
              回测整体结果：{presenterLine}
            </div>
          )}
          <div className="scan-detail__bt-note">
            （此处与表格中的回测信息由机会后处理「会话展示」提供）
          </div>
        </div>
      ) : null}
    </div>
  );
}

function StockCell({ row }) {
  const name = String(row?.stock_name || '').trim() || row?.stock_id || '—';
  const code = String(row?.stock_id || '').trim();
  return (
    <div className="scan-detail__stock">
      <div className="scan-detail__stock-name">{name}</div>
      {code && code !== name ? (
        <div className="scan-detail__stock-code">{code}</div>
      ) : null}
    </div>
  );
}

function OpportunityInfoCell({ row }) {
  return (
    <div className="scan-detail__opp-info">
      <div className="scan-detail__opp-primary">
        <span className="scan-detail__opp-kv">
          <span className="scan-detail__opp-k">进入价格</span>
          <span className="scan-detail__opp-v">{formatPrice(row?.trigger_price)}</span>
        </span>
        <span className="scan-detail__opp-primary-sep">｜</span>
        <span className="scan-detail__opp-kv">
          <span className="scan-detail__opp-k">股数</span>
          <span className="scan-detail__opp-v">{formatQty(row?.qty)}</span>
        </span>
      </div>
      <div className="scan-detail__opp-cost">
        <span className="scan-detail__opp-k">总投资成本</span>
        <span className="scan-detail__opp-v scan-detail__opp-v--muted">
          {formatNotional(row?.notional)} 元
        </span>
      </div>
    </div>
  );
}

function MetricCell({ value, tone = '' }) {
  return (
    <div
      className={[
        'scan-detail__metric',
        tone === 'pos' ? 'scan-detail__metric--pos' : '',
        tone === 'neg' ? 'scan-detail__metric--neg' : '',
      ].filter(Boolean).join(' ')}
    >
      {value}
    </div>
  );
}

function avgReturnTone(raw) {
  const n = Number(raw);
  if (!Number.isFinite(n) || n === 0) return '';
  return n > 0 ? 'pos' : 'neg';
}

/** 默认两列（对齐邮件：股票 + 机会信息） */
export function buildOpportunityColumns({ withPresenter = false } = {}) {
  const cols = [
    {
      field: 'stock',
      headerName: '股票',
      minWidth: 148,
      flex: withPresenter ? 0.7 : 0.85,
      sortable: false,
      valueGetter: (params) => params?.row?.stock_name || params?.row?.stock_id || '',
      renderCell: (params) => <StockCell row={params.row} />,
    },
    {
      field: 'opportunity',
      headerName: '机会信息',
      minWidth: 200,
      flex: withPresenter ? 1 : 1.2,
      sortable: false,
      valueGetter: (params) => params?.row?.trigger_price ?? '',
      renderCell: (params) => <OpportunityInfoCell row={params.row} />,
    },
  ];
  if (withPresenter) {
    cols.push(
      {
        field: 'bt_completed',
        headerName: '回测次数',
        width: 88,
        minWidth: 88,
        maxWidth: 100,
        align: 'right',
        headerAlign: 'right',
        sortable: true,
        renderCell: (params) => (
          <MetricCell
            value={params?.row?.bt_completed == null ? '—' : String(params.row.bt_completed)}
          />
        ),
      },
      {
        field: 'bt_win_rate',
        headerName: '胜率',
        width: 88,
        minWidth: 88,
        maxWidth: 100,
        align: 'right',
        headerAlign: 'right',
        sortable: true,
        renderCell: (params) => (
          <MetricCell value={formatPct(params?.row?.bt_win_rate)} />
        ),
      },
      {
        field: 'bt_avg_return',
        headerName: '平均收益',
        width: 100,
        minWidth: 100,
        maxWidth: 120,
        align: 'right',
        headerAlign: 'right',
        sortable: true,
        renderCell: (params) => (
          <MetricCell
            value={formatPct(params?.row?.bt_avg_return)}
            tone={avgReturnTone(params?.row?.bt_avg_return)}
          />
        ),
      },
    );
  }
  return cols;
}
