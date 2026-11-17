import React, { useMemo } from 'react';
import Icon from 'ui/icon/icon';
import { MONTH_CALENDAR_DENSITY_TOKENS, pickToken } from 'ui/tokens';
import {
  WEEKDAY_HEADS_ZH,
  buildMonthCells,
  monthTitle,
  shiftMonth,
} from '../monthUtils';
import './style.scss';

/**
 * 月历壳（周一开始）。
 * 业务事件 / 交易日标注通过 renderDay 或 dayProps 由上层提供；不内置买卖机会逻辑。
 *
 * @example
 * <MonthCalendar year={2026} month={4} selected="2026-04-10" density="sm" />
 * <MonthCalendar
 *   year={y} month={m}
 *   density="md"
 *   onMonthChange={({ year, month }) => …}
 *   renderDay={(date) => <Tag status="info">买</Tag>}
 * />
 */
function MonthCalendar({
  year,
  month,
  selected = '',
  today = '',
  density = 'sm',
  showNav = true,
  disabledDates,
  onMonthChange,
  onDayClick,
  renderDay,
  getDayProps,
  className = '',
  ...rest
}) {
  const densityToken = pickToken(density, MONTH_CALENDAR_DENSITY_TOKENS, 'sm');
  const y = Number(year) || new Date().getFullYear();
  const m = Number(month) || (new Date().getMonth() + 1);
  const cells = useMemo(() => buildMonthCells(y, m), [y, m]);

  const disabledSet = useMemo(() => {
    if (!disabledDates) return null;
    if (disabledDates instanceof Set) return disabledDates;
    return new Set(Array.isArray(disabledDates) ? disabledDates : []);
  }, [disabledDates]);

  const rootClass = [
    'ntq-month-calendar',
    `ntq-month-calendar--${densityToken}`,
    className,
  ].filter(Boolean).join(' ');

  const go = (delta) => {
    if (typeof onMonthChange !== 'function') return;
    onMonthChange(shiftMonth(y, m, delta));
  };

  return (
    <div className={rootClass} {...rest}>
      {showNav ? (
        <div className="ntq-month-calendar__nav">
          <button
            type="button"
            className="ntq-month-calendar__nav-btn"
            aria-label="上个月"
            disabled={typeof onMonthChange !== 'function'}
            onClick={() => go(-1)}
          >
            <Icon name="arrowBack" size="sm" />
          </button>
          <div className="ntq-month-calendar__title">{monthTitle(y, m)}</div>
          <button
            type="button"
            className="ntq-month-calendar__nav-btn"
            aria-label="下个月"
            disabled={typeof onMonthChange !== 'function'}
            onClick={() => go(1)}
          >
            <Icon name="chevronRight" size="sm" />
          </button>
        </div>
      ) : (
        <div className="ntq-month-calendar__title ntq-month-calendar__title--solo">
          {monthTitle(y, m)}
        </div>
      )}

      <div
        className="ntq-month-calendar__grid"
        role="grid"
        aria-label={monthTitle(y, m)}
      >
        {WEEKDAY_HEADS_ZH.map((label) => (
          <div key={label} className="ntq-month-calendar__head" role="columnheader">
            {label}
          </div>
        ))}
        {cells.map((date, index) => {
          if (!date) {
            return (
              <div
                key={`pad-${index}`}
                className="ntq-month-calendar__cell is-pad"
                role="gridcell"
              />
            );
          }
          const dayNum = Number(date.slice(8));
          const isSelected = selected && date === selected;
          const isToday = today && date === today;
          const isDisabled = disabledSet ? disabledSet.has(date) : false;
          const extra = typeof getDayProps === 'function' ? (getDayProps(date) || {}) : {};
          const clickable = typeof onDayClick === 'function' && !isDisabled;

          const cellClass = [
            'ntq-month-calendar__cell',
            isSelected ? 'is-selected' : '',
            isToday ? 'is-today' : '',
            isDisabled ? 'is-disabled' : '',
            extra.className || '',
          ].filter(Boolean).join(' ');

          const body = typeof renderDay === 'function' ? renderDay(date) : null;

          return (
            <div
              key={date}
              className={cellClass}
              role="gridcell"
              aria-selected={isSelected || undefined}
              data-date={date}
            >
              {clickable ? (
                <button
                  type="button"
                  className="ntq-month-calendar__day-btn"
                  disabled={isDisabled}
                  onClick={() => onDayClick(date)}
                >
                  <span className="ntq-month-calendar__num">{dayNum}</span>
                </button>
              ) : (
                <span className="ntq-month-calendar__num">{dayNum}</span>
              )}
              {body ? (
                <div className="ntq-month-calendar__body">{body}</div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default MonthCalendar;
