import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { Box, Stack, Typography } from '@mui/material';
import ChartPanel from 'views/chartPanel';
import { previewWho } from './seriesRelationConstants';

function fmtNum(v, digits = 2) {
  if (v == null || v === '') return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v);
  return n.toFixed(digits);
}

function corrCellStyle(r) {
  if (r == null || !Number.isFinite(Number(r))) {
    return { background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.4)' };
  }
  const v = Number(r);
  const a = Math.min(1, Math.abs(v));
  if (v >= 0) {
    return {
      background: `rgba(34, 197, 94, ${0.12 + a * 0.55})`,
      color: a > 0.45 ? 'rgba(255,255,255,0.92)' : 'rgba(187, 247, 208, 0.95)',
    };
  }
  return {
    background: `rgba(239, 68, 68, ${0.12 + a * 0.55})`,
    color: a > 0.45 ? 'rgba(255,255,255,0.92)' : 'rgba(254, 202, 202, 0.95)',
  };
}

function stabilityMeta(rolling) {
  const tag = String(rolling?.stability || '');
  if (tag === 'stable') {
    return { label: '稳定', tone: 'stable' };
  }
  if (tag === 'mostly_stable') {
    return { label: '基本稳', tone: 'mostly' };
  }
  if (tag === 'unstable') {
    return { label: '不稳', tone: 'unstable' };
  }
  return { label: '待判', tone: 'unknown' };
}

function pairHeadline(row) {
  const p = row?.pearson;
  const rel = String(row?.relation || '');
  if (p == null || !Number.isFinite(Number(p))) {
    return { text: '样本不足', tone: 'muted' };
  }
  const abs = Math.abs(Number(p));
  const num = fmtNum(p, 2);
  if (rel === 'positive' || (rel !== 'negative' && Number(p) > 0.15)) {
    return { text: `${num} 同向`, tone: 'pos' };
  }
  if (rel === 'negative' || Number(p) < -0.15) {
    return { text: `${num} 反向`, tone: 'neg' };
  }
  return { text: `${num} 偏弱`, tone: 'muted' };
}

function pairBlurb(row) {
  const core = row?.core && typeof row.core === 'object' ? row.core : {};
  const rolling = row?.supplement?.rolling;
  const stab = stabilityMeta(rolling);
  const rel = String(row?.relation || '');
  const weaker = rolling
    && Number.isFinite(Number(rolling.mean))
    && Number.isFinite(Number(rolling.recent))
    && Math.abs(Number(rolling.recent)) + 0.08 < Math.abs(Number(rolling.mean));

  if (rel === 'positive') {
    return weaker
      ? '多数时候同涨同跌，最近同步性略弱。'
      : '多数时候同涨同跌，走势较合拍。';
  }
  if (rel === 'negative') {
    if (stab.tone === 'unstable') {
      return '整体反向强，但滚动窗口里时有时无。';
    }
    return '一个涨时另一个常跌，偶尔方向对调。';
  }
  const text = String(core.relation_text || '').trim();
  if (text.length > 48) return `${text.slice(0, 48)}…`;
  return text || '关系偏弱或不稳定，结论请谨慎。';
}

function buildCorrMatrix(series, pairwise) {
  const ids = series.map((s) => String(s.id || ''));
  const labels = series.map((s) => String(s.label || s.id || '?'));
  const map = new Map();
  pairwise.forEach((row) => {
    const a = String(row.a || '');
    const b = String(row.b || '');
    if (!a || !b) return;
    map.set(`${a}|${b}`, row.pearson);
    map.set(`${b}|${a}`, row.pearson);
  });
  const cells = ids.map((idI, i) => ids.map((idJ, j) => {
    if (i === j) return 1;
    const v = map.get(`${idI}|${idJ}`);
    return v == null ? null : Number(v);
  }));
  return { labels, cells };
}

function RelationMatrix({ series, pairwise }) {
  const { labels, cells } = useMemo(
    () => buildCorrMatrix(series, pairwise),
    [series, pairwise],
  );
  if (!labels.length) return null;
  return (
    <Box className="ntq-srel-matrix">
      <div
        className="ntq-srel-matrix__grid"
        style={{
          gridTemplateColumns: `minmax(88px, max-content) repeat(${labels.length}, minmax(88px, 1fr))`,
        }}
      >
        <div className="ntq-srel-matrix__corner" />
        {labels.map((lab) => (
          <div key={`h-${lab}`} className="ntq-srel-matrix__head" title={lab}>
            {lab}
          </div>
        ))}
        {labels.map((rowLab, i) => (
          <React.Fragment key={`r-${rowLab}-${i}`}>
            <div className="ntq-srel-matrix__row-label" title={rowLab}>{rowLab}</div>
            {cells[i].map((v, j) => (
              <div
                key={`c-${i}-${j}`}
                className="ntq-srel-matrix__cell"
                style={corrCellStyle(v)}
                title={`${labels[i]} vs ${labels[j]}: ${fmtNum(v, 3)}`}
              >
                {v == null ? '—' : fmtNum(v, 2)}
              </div>
            ))}
          </React.Fragment>
        ))}
      </div>
      <Typography variant="caption" color="text.secondary" className="ntq-srel-matrix__legend">
        红 = 反向 · 绿 = 同向 · 色深 = 关系强（Pearson）
      </Typography>
    </Box>
  );
}

function PairCard({ row }) {
  const rolling = row?.supplement?.rolling;
  const stab = stabilityMeta(rolling);
  const headline = pairHeadline(row);
  const left = row.label_a || row.a || '?';
  const right = row.label_b || row.b || '?';
  const lag = row.best_lag_days;
  return (
    <Box className="ntq-srel-pair-card">
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
        <Typography variant="subtitle2" className="ntq-srel-pair-card__title">
          {left} vs {right}
        </Typography>
        <span className={`ntq-srel-pill ntq-srel-pill--${stab.tone}`}>{stab.label}</span>
      </Stack>
      <Typography className={`ntq-srel-pair-card__headline ntq-srel-pair-card__headline--${headline.tone}`}>
        {headline.text}
      </Typography>
      <Stack direction="row" spacing={1.5} className="ntq-srel-pair-card__metrics" flexWrap="wrap" useFlexGap>
        <span>滞后 {lag == null ? '—' : `${lag} 日`}</span>
        <span>β {fmtNum(row.beta_b_on_a, 1)}</span>
        <span>R² {fmtNum(row.scale_r2, 2)}</span>
      </Stack>
      <Typography variant="body2" color="text.secondary" className="ntq-srel-pair-card__blurb">
        {pairBlurb(row)}
      </Typography>
    </Box>
  );
}

PairCard.propTypes = {
  row: PropTypes.object.isRequired,
};

function SeriesRelationReport({
  results = null,
  chartOption = null,
  strategyOptions = [],
}) {
  if (!results?.has_results) {
    return (
      <Typography variant="body2" color="text.secondary">
        运行后将在此展示结构化报告。
      </Typography>
    );
  }

  const meta = results.meta && typeof results.meta === 'object' ? results.meta : {};
  const summary = results.summary && typeof results.summary === 'object' ? results.summary : {};
  const series = Array.isArray(meta.series) ? meta.series : [];
  const pairwise = Array.isArray(summary.pairwise) ? summary.pairwise : [];
  const dateMin = series.reduce((acc, s) => {
    const d = String(s.date_min || '');
    if (!d) return acc;
    return !acc || d < acc ? d : acc;
  }, '');
  const dateMax = series.reduce((acc, s) => {
    const d = String(s.date_max || '');
    if (!d) return acc;
    return !acc || d > acc ? d : acc;
  }, '');

  return (
    <Box className="ntq-srel-showcase">
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        spacing={1.5}
        className="ntq-srel-showcase__head"
      >
        <Box>
          <Typography className="ntq-srel-showcase__eyebrow">SERIES RELATION</Typography>
          <Typography variant="h5" className="ntq-srel-showcase__title">
            {meta.key || results.key || '—'}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap className="ntq-srel-showcase__tags">
          <span className="ntq-srel-tag">
            {summary.series_count ?? series.length ?? '—'} 系列
          </span>
          <span className="ntq-srel-tag">
            {summary.calendar_len ?? '—'} 交易日
          </span>
          <span className="ntq-srel-tag">
            {meta.normalize || '—'} · {meta.fill || '—'}
          </span>
        </Stack>
      </Stack>

      {series.length ? (
        <Box className="ntq-srel-showcase__section">
          <Typography variant="subtitle1" className="ntq-srel-showcase__section-title" sx={{ mb: 1.25 }}>
            参与者
          </Typography>
          <div className="ntq-srel-participant-grid">
            {series.map((item) => (
              <Box key={String(item.id)} className="ntq-srel-participant">
                <Typography variant="subtitle2" className="ntq-srel-participant__label">
                  {item.label || item.id}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  {previewWho(item, strategyOptions)}
                </Typography>
              </Box>
            ))}
          </div>
        </Box>
      ) : null}

      <Box className="ntq-srel-showcase__section">
        <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mb: 1.25 }}>
          <Box>
            <Typography variant="subtitle1" className="ntq-srel-showcase__section-title">
              归一化走势
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {dateMin && dateMax ? `${dateMin} – ${dateMax}` : '按全局 normalize 后的曲线'}
            </Typography>
          </Box>
        </Stack>
        {chartOption ? (
          <ChartPanel
            title="标准化 / 归一化值"
            tip="纵轴含义随全局 Normalize（如 zscore）变化"
            option={chartOption}
            height={340}
            framed={false}
          />
        ) : (
          <Typography variant="body2" color="text.secondary">暂无曲线数据</Typography>
        )}
      </Box>

      <Box className="ntq-srel-showcase__section">
        <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mb: 1.25 }}>
          <Box>
            <Typography variant="subtitle1" className="ntq-srel-showcase__section-title">
              关系矩阵
            </Typography>
            <Typography variant="caption" color="text.secondary">Pearson</Typography>
          </Box>
        </Stack>
        {pairwise.length ? (
          <RelationMatrix series={series} pairwise={pairwise} />
        ) : (
          <Typography variant="body2" color="text.secondary">
            未做两两分析（analyze=false 或系列不足）。
          </Typography>
        )}
      </Box>

      <Box className="ntq-srel-showcase__section">
        <Typography variant="subtitle1" className="ntq-srel-showcase__section-title" sx={{ mb: 1.25 }}>
          两两结论
        </Typography>
        {pairwise.length ? (
          <div className="ntq-srel-pair-grid">
            {pairwise.map((row, index) => (
              <PairCard key={`${row.a}-${row.b}-${index}`} row={row} />
            ))}
          </div>
        ) : (
          <Typography variant="body2" color="text.secondary">无配对结论</Typography>
        )}
      </Box>
    </Box>
  );
}

SeriesRelationReport.propTypes = {
  results: PropTypes.object,
  chartOption: PropTypes.object,
  strategyOptions: PropTypes.arrayOf(PropTypes.object),
};

export default SeriesRelationReport;
