import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { ChartPanel, Heading, Tag } from 'ui';
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
    return { label: '稳定', tone: 'stable', status: 'success' };
  }
  if (tag === 'mostly_stable') {
    return { label: '基本稳', tone: 'mostly', status: 'warning' };
  }
  if (tag === 'unstable') {
    return { label: '不稳', tone: 'unstable', status: 'error' };
  }
  return { label: '待判', tone: 'unknown', status: 'neutral' };
}

function pairHeadline(row) {
  const p = row?.pearson;
  const rel = String(row?.relation || '');
  if (p == null || !Number.isFinite(Number(p))) {
    return { text: '样本不足', tone: 'muted' };
  }
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
    <div className="ntq-srel-matrix">
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
      <p className="ntq-muted ntq-srel-matrix__legend">
        红 = 反向 · 绿 = 同向 · 色深 = 关系强（Pearson）
      </p>
    </div>
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
    <article className="ntq-srel-pair-card">
      <header className="ntq-srel-pair-card__head">
        <h4 className="ntq-srel-pair-card__title">
          {left} vs {right}
        </h4>
        <Tag
          status={stab.status}
          variant={stab.tone === 'unknown' ? 'outline' : 'solid'}
        >
          {stab.label}
        </Tag>
      </header>
      <p className={`ntq-srel-pair-card__headline ntq-srel-pair-card__headline--${headline.tone}`}>
        {headline.text}
      </p>
      <div className="ntq-srel-pair-card__metrics">
        <span>滞后 {lag == null ? '—' : `${lag} 日`}</span>
        <span>β {fmtNum(row.beta_b_on_a, 1)}</span>
        <span>R² {fmtNum(row.scale_r2, 2)}</span>
      </div>
      <p className="ntq-muted ntq-srel-pair-card__blurb">{pairBlurb(row)}</p>
    </article>
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
    return <p className="ntq-muted">运行后将在此展示结构化报告。</p>;
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
    <div className="ntq-srel-showcase">
      <div className="ntq-srel-showcase__head">
        <div>
          <p className="ntq-srel-showcase__eyebrow">SERIES RELATION</p>
          <Heading level="h3" gap="none" className="ntq-srel-showcase__title">
            {meta.key || results.key || '—'}
          </Heading>
        </div>
        <div className="ntq-srel-showcase__tags">
          <Tag status="neutral" variant="outline">
            {summary.series_count ?? series.length ?? '—'} 系列
          </Tag>
          <Tag status="neutral" variant="outline">
            {summary.calendar_len ?? '—'} 交易日
          </Tag>
          <Tag status="info" variant="outline">
            {meta.normalize || '—'} · {meta.fill || '—'}
          </Tag>
        </div>
      </div>

      {series.length ? (
        <section className="ntq-srel-showcase__section">
          <Heading level="h4" gap="none">参与者</Heading>
          <div className="ntq-srel-participant-grid">
            {series.map((item) => (
              <div key={String(item.id)} className="ntq-srel-participant">
                <div className="ntq-srel-participant__label">
                  {item.label || item.id}
                </div>
                <div className="ntq-muted ntq-srel-participant__who">
                  {previewWho(item, strategyOptions)}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="ntq-srel-showcase__section">
        <div className="ntq-srel-showcase__section-head">
          <Heading level="h4" gap="none">归一化走势</Heading>
          <p className="ntq-muted">
            {dateMin && dateMax ? `${dateMin} – ${dateMax}` : '按全局 normalize 后的曲线'}
          </p>
        </div>
        {chartOption ? (
          <ChartPanel
            title="标准化 / 归一化值"
            tip="纵轴含义随全局 Normalize（如 zscore）变化"
            option={chartOption}
            height={340}
            framed={false}
          />
        ) : (
          <p className="ntq-muted">暂无曲线数据</p>
        )}
      </section>

      <section className="ntq-srel-showcase__section">
        <div className="ntq-srel-showcase__section-head">
          <Heading level="h4" gap="none">关系矩阵</Heading>
          <p className="ntq-muted">Pearson</p>
        </div>
        {pairwise.length ? (
          <RelationMatrix series={series} pairwise={pairwise} />
        ) : (
          <p className="ntq-muted">未做两两分析（analyze=false 或系列不足）。</p>
        )}
      </section>

      <section className="ntq-srel-showcase__section">
        <Heading level="h4" gap="none">两两结论</Heading>
        {pairwise.length ? (
          <div className="ntq-srel-pair-grid">
            {pairwise.map((row, index) => (
              <PairCard key={`${row.a}-${row.b}-${index}`} row={row} />
            ))}
          </div>
        ) : (
          <p className="ntq-muted">无配对结论</p>
        )}
      </section>
    </div>
  );
}

SeriesRelationReport.propTypes = {
  results: PropTypes.object,
  chartOption: PropTypes.object,
  strategyOptions: PropTypes.arrayOf(PropTypes.object),
};

export default SeriesRelationReport;
