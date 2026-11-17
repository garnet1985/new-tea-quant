import React from 'react';
import { Button, DefinitionList, Dialog } from 'ui';
import {
  buildMonthCells,
  calendarActionDetail,
  calendarActionLabel,
  calendarActionNote,
  formatMoney,
  monthTitle,
} from './decisionFormat';

const WEEKDAY_HEADS = ['一', '二', '三', '四', '五', '六', '日'];

export function CalendarActionDialog({ action, open, onClose }) {
  if (!action) {
    return (
      <Dialog
        open={open}
        onClose={onClose}
        title="成交"
        size="sm"
        actions={<Button variant="ghost" onClick={onClose}>关闭</Button>}
      />
    );
  }
  const note = String(action.note || '').trim();
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`${action.side === 'sell' ? '卖出' : '买入'}明细`}
      size="sm"
      actions={<Button variant="primary" onClick={onClose}>关闭</Button>}
    >
      <DefinitionList
        items={[
          { label: '标的', value: action.name || action.ticker || '—' },
          action.ticker && action.ticker !== action.name
            ? { label: '代码', value: action.ticker }
            : null,
          { label: '股数', value: `${Number(action.shares || 0).toLocaleString()} 股` },
          { label: '金额', value: formatMoney(action.amount) },
        ].filter(Boolean)}
      />
      {note ? (
        <>
          <span className="ntq-decision-subtitle ntq-decision-strong">
            买入笔记
          </span>
          <span className="decision-buy-note">
            {note}
          </span>
        </>
      ) : null}
    </Dialog>
  );
}

export function CalendarEventChip({ className, label, detail, note, onClick }) {
  const chipClass = `decision-cal-event ${className || ''}`.trim();
  const noteText = String(note || '').trim();
  const tip = [detail || label, noteText].filter(Boolean).join('\n');
  const body = onClick ? (
    <button type="button" className={chipClass} title={tip || undefined} onClick={onClick}>
      {label}
    </button>
  ) : (
    <span className={chipClass} title={tip || undefined}>{label}</span>
  );
  return body;
}

export function MonthGrid({ year, month, clockDate, days, rangeStart, rangeEnd, onActionClick }) {
  const cells = buildMonthCells(year, month);
  return (
    <div className="decision-month-grid" role="grid" aria-label={`${monthTitle(year, month)} 交易日历`}>
      {WEEKDAY_HEADS.map((label) => (
        <div key={label} className="decision-month-head">
          {label}
        </div>
      ))}
      {cells.map((date, index) => {
        if (!date) {
          return <div key={`empty-${index}`} className="decision-month-cell is-pad" />;
        }
        const outOfRange = (rangeStart && date < rangeStart) || (rangeEnd && date > rangeEnd);
        const future = date > clockDate;
        const day = !outOfRange && !future ? days[date] : null;
        const oppCount = Number(day?.oppCount) || 0;
        const actions = Array.isArray(day?.actions) ? day.actions : [];
        const hasEvents = oppCount > 0 || actions.length > 0;
        return (
          <div key={date} className={[
              'decision-month-cell',
              date === clockDate ? 'is-now' : '',
              outOfRange ? 'is-out' : '',
              future ? 'is-future' : '',
              hasEvents ? 'has-events' : '',
            ].filter(Boolean).join(' ')}>
            <span className="decision-month-cell__num">{Number(date.slice(8))}</span>
            <span className="decision-month-cell__events">
              {oppCount > 0 ? (
                <CalendarEventChip
                  className="is-opp"
                  label={`发现${oppCount}个机会`}
                />
              ) : null}
              {actions.map((action, actionIndex) => (
                <CalendarEventChip
                  key={`${action.side}-${action.ticker}-${actionIndex}`}
                  className={`is-${action.side}`}
                  label={calendarActionLabel(action)}
                  detail={calendarActionDetail(action)}
                  note={calendarActionNote(action)}
                  onClick={onActionClick ? () => onActionClick(action) : undefined}
                />
              ))}
            </span>
          </div>
        );
      })}
    </div>
  );
}
