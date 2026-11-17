import React from 'react';
import { Button, Dialog, Icon, TextArea } from 'ui';
import { formatMoney } from './decisionFormat';
import {
  cashFromShares,
  lotRule,
  opportunityStockLabel,
  shareStepJump,
} from './decisionPlayHelpers';

export const NOTE_MAX = 2000;

export function SuggestedSharesCell({ suggestedCash, suggestedShares, basis, held }) {
  if (held) return '—';
  const hasCash = suggestedCash != null && suggestedCash > 0;
  const hasShares = suggestedShares != null && suggestedShares > 0;
  const basisEl = basis ? <span className="decision-suggest-basis">{basis}</span> : null;
  if (!hasShares) {
    return (
      <span className="decision-suggest-cell">
        —
        {basisEl}
      </span>
    );
  }
  return (
    <span className="decision-suggest-cell">
      {`${Number(suggestedShares).toLocaleString()} 股`}
      {hasCash ? (
        <span className="decision-suggest-shares">约 {Number(suggestedCash).toLocaleString()} 元</span>
      ) : null}
      {basisEl}
    </span>
  );
}

export function ShareCapsule({
  disabled,
  draft,
  error,
  lotStep,
  ticker,
  onDraftChange,
  onStep,
}) {
  const jump = shareStepJump(lotStep);
  const stopRow = (event) => event.stopPropagation();
  return (
    <span className={`decision-shares-capsule${error ? ' is-error' : ''}${disabled ? ' is-disabled' : ''}`}>
      <button
        type="button"
        className="decision-capsule-btn"
        disabled={disabled}
        aria-label={`减少 ${jump} 股`}
        onClick={(event) => {
          event.stopPropagation();
          onStep(-1);
        }}
        onMouseDown={(event) => {
          event.preventDefault();
          event.stopPropagation();
        }}
      >
        −
      </button>
      <input
        className="decision-capsule-input"
        type="text"
        inputMode="numeric"
        disabled={disabled}
        value={draft}
        placeholder="股数"
        aria-label={`投资股数 ${ticker || ''}`}
        onClick={stopRow}
        onMouseDown={stopRow}
        onChange={(event) => onDraftChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowUp') {
            event.preventDefault();
            onStep(1);
          }
          if (event.key === 'ArrowDown') {
            event.preventDefault();
            onStep(-1);
          }
        }}
      />
      <button
        type="button"
        className="decision-capsule-btn"
        disabled={disabled}
        aria-label={`增加 ${jump} 股`}
        onClick={(event) => {
          event.stopPropagation();
          onStep(1);
        }}
        onMouseDown={(event) => {
          event.preventDefault();
          event.stopPropagation();
        }}
      >
        +
      </button>
    </span>
  );
}

export function InvestOpenCell({ disabled, shares, note, onOpen }) {
  const n = Number(shares) || 0;
  const noteText = String(note || '').trim();
  return (
    <span className="decision-invest-cell">
      <Button
        variant={n > 0 ? 'glass' : 'primary'}
        className="decision-invest-open"
        disabled={disabled}
        onClick={(event) => {
          event.stopPropagation();
          onOpen();
        }}
      >
        {n > 0 ? `已投 ${n.toLocaleString()} 股` : '投资'}
      </Button>
      {n > 0 && noteText ? (
        <span
          className="decision-invest-note-icon"
          title={noteText}
          aria-label="买入笔记"
          onClick={(event) => event.stopPropagation()}
          onMouseDown={(event) => event.stopPropagation()}
        >
          <Icon name="chat" size="sm" />
        </span>
      ) : null}
    </span>
  );
}

export function InvestDialog({
  row,
  open,
  shares,
  note,
  error,
  submitting,
  onSharesChange,
  onNoteChange,
  onStep,
  onApplySuggested,
  onClear,
  onCancel,
  onConfirm,
}) {
  const { lotStep } = lotRule(row || {});
  const parsed = Number(shares);
  const notional = Number.isFinite(parsed) && parsed > 0
    ? formatMoney(cashFromShares(parsed, row?.price))
    : '';
  const hasSuggested = row?.suggestedShares != null && Number(row.suggestedShares) > 0;
  const suggestedCash = row?.suggestedCash != null && Number(row.suggestedCash) > 0
    ? Number(row.suggestedCash)
    : null;
  const picked = Number(row?.pickedShares || 0) > 0;
  return (
    <Dialog
      open={open}
      onClose={submitting ? undefined : onCancel}
      title={`投资${row ? ` ${opportunityStockLabel(row)}` : ''}`}
      size="sm"
      actions={(
        <>
          {picked ? (
            <Button variant="glass" onClick={onClear} disabled={submitting}>
              取消本次投资
            </Button>
          ) : null}
          <Button variant="primary" onClick={onConfirm} disabled={submitting}>
            确认
          </Button>
        </>
      )}
    >
      {row ? (
        <div className="ntq-decision-stack" style={{ display: 'flex', flexDirection: 'column', gap: '1.0rem' }}>
          <span className="ntq-muted">
            成交价 {formatMoney(row.price)}
            {notional ? ` · 约 ${notional}` : ''}
          </span>
          {hasSuggested ? (
            <div>
              <span className="ntq-decision-subtitle ntq-decision-strong">
                推荐买入
              </span>
              <Button variant="glass" onClick={onApplySuggested} disabled={submitting}>
                {`${Number(row.suggestedShares).toLocaleString()} 股`}
                {suggestedCash != null ? `（约 ${Number(suggestedCash).toLocaleString()} 元）` : ''}
              </Button>
              {row.suggestedBasis ? (
                <div className="ntq-caption ntq-muted">
                  {row.suggestedBasis}
                </div>
              ) : null}
            </div>
          ) : (
            <span className="ntq-muted">暂无推荐买入</span>
          )}
          <div>
            <span className="ntq-decision-subtitle ntq-decision-strong">
              股数
            </span>
            <ShareCapsule
              disabled={submitting}
              draft={shares}
              error={error}
              lotStep={lotStep}
              ticker={row.ticker}
              onDraftChange={onSharesChange}
              onStep={onStep}
            />
            {error ? (
              <div className="ntq-caption ntq-decision-error">
                {error}
              </div>
            ) : null}
          </div>
          <TextArea label="买入笔记（可选）" placeholder="为什么买、仓位想法、风险…" value={note} onChange={(event) => onNoteChange(event.target.value)} fullWidth disabled={submitting} inputProps={{ maxLength: NOTE_MAX }} maxWidth={false} hint={`${String(note || '').length}/${NOTE_MAX}`} rows={3} />
        </div>
      ) : null}
    </Dialog>
  );
}
