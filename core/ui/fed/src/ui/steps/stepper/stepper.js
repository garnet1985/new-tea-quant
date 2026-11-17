import React from 'react';
import ProgressRing from 'ui/progress/progressRing';
import { STEPPER_ITEM_STATUSES, pickToken } from 'ui/tokens';
import './style.scss';

/**
 * 解析单步视觉 class（对齐回测 stepper）。
 * activeId 管「当前选中」；item.status 管执行态。
 */
function resolveVisual(item, activeId, showProgress) {
  const selected = item.id === activeId;
  const status = pickToken(item.status, STEPPER_ITEM_STATUSES, 'idle');
  const pct = Number(item.progress);
  const safePct = Number.isFinite(pct) ? Math.max(0, Math.min(100, pct)) : 0;

  if (status === 'failed') return { kind: 'failed' };
  if (status === 'running') {
    if (showProgress) return { kind: 'running', pct: safePct };
    return { kind: selected ? 'active' : 'idle' };
  }
  if (status === 'pending') {
    if (showProgress) return { kind: 'pending' };
    return { kind: selected ? 'active' : 'idle' };
  }
  if (status === 'done') return { kind: selected ? 'done-active' : 'done' };
  if (selected) return { kind: 'active' };
  return { kind: 'idle' };
}

function StepHit({
  item,
  className,
  onItemClick,
  children,
}) {
  const {
    href,
    to,
    component,
    onClick,
    disabled = false,
    label,
    id,
  } = item;

  const Comp = component || (href ? 'a' : 'button');
  const interactive = Boolean(href || to || onClick || onItemClick || component);

  const handleClick = (event) => {
    if (disabled) {
      event.preventDefault();
      return;
    }
    if (typeof onClick === 'function') onClick(event, item);
    if (typeof onItemClick === 'function') onItemClick(item, event);
  };

  const handleKeyDown = (event) => {
    if (Comp !== 'button' && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      handleClick(event);
    }
  };

  const shared = {
    className,
    title: label,
    'aria-label': label || String(id),
    'aria-disabled': disabled || undefined,
    onClick: interactive ? handleClick : undefined,
    onKeyDown: interactive && Comp !== 'button' ? handleKeyDown : undefined,
  };

  if (Comp === 'button') {
    return (
      <button
        type="button"
        disabled={disabled}
        tabIndex={interactive ? 0 : -1}
        {...shared}
      >
        {children}
      </button>
    );
  }

  const linkProps = {
    ...shared,
    tabIndex: disabled ? -1 : 0,
    role: Comp === 'a' ? undefined : 'link',
  };
  if (href) linkProps.href = href;
  if (to != null) linkProps.to = to;

  return (
    <Comp {...linkProps}>
      {children}
    </Comp>
  );
}

/**
 * 步骤条（回测视觉）。纯展示 + 可选点击跳转，不含路由/会话。
 *
 * @example
 * <Stepper
 *   activeId="price"
 *   items={[
 *     { id: 'enum', label: '机会盘点', status: 'done', href: '#enum' },
 *     { id: 'price', label: '价格回测', status: 'running', progress: 42 },
 *     { id: 'portfolio', label: '投资模拟', status: 'idle' },
 *   ]}
 * />
 * <Stepper showProgress={false} activeId="enum" items={items} />
 */
function Stepper({
  items = [],
  activeId = null,
  showProgress = true,
  onItemClick,
  className = '',
  'aria-label': ariaLabel = '步骤',
}) {
  const list = Array.isArray(items) ? items : [];
  const count = list.length;

  const rootClass = [
    'ntq-stepper',
    showProgress ? '' : 'ntq-stepper--no-progress',
    className,
  ].filter(Boolean).join(' ');

  return (
    <nav
      className={rootClass}
      aria-label={ariaLabel}
      style={{ '--ntq-stepper-count': count }}
    >
      {list.map((item, idx) => {
        const visual = resolveVisual(item, activeId, showProgress);
        const isLast = idx === count - 1;
        const no = item.no != null ? item.no : idx + 1;
        const next = list[idx + 1];
        const connectorDone = Boolean(
          next && pickToken(next.status, STEPPER_ITEM_STATUSES, 'idle') === 'done',
        );
        const showRing = showProgress
          && (visual.kind === 'running' || visual.kind === 'pending');

        return (
          <StepHit
            key={item.id != null ? item.id : idx}
            item={item}
            onItemClick={onItemClick}
            className="ntq-stepper__hit"
          >
            <span className={`ntq-stepper__item${isLast ? ' ntq-stepper__item--last' : ''}`}>
              {!isLast ? (
                <span
                  className={[
                    'ntq-stepper__connector',
                    connectorDone ? 'ntq-stepper__connector--done' : '',
                  ].filter(Boolean).join(' ')}
                  aria-hidden
                />
              ) : null}
              <span
                className={[
                  'ntq-stepper__step',
                  `ntq-stepper__step--${visual.kind}`,
                ].join(' ')}
              >
                <span className="ntq-stepper__ring-wrap">
                  {showRing ? (
                    <ProgressRing
                      value={visual.kind === 'running' ? visual.pct : null}
                      size="md"
                      className={[
                        'ntq-stepper__ring',
                        visual.kind === 'pending' ? 'ntq-stepper__ring--pending' : '',
                      ].filter(Boolean).join(' ')}
                      aria-hidden
                    >
                      <span className="ntq-stepper__circle">
                        <span className="ntq-stepper__num">{no}</span>
                      </span>
                    </ProgressRing>
                  ) : (
                    <span className="ntq-stepper__circle">
                      <span className="ntq-stepper__num">{no}</span>
                    </span>
                  )}
                </span>
              </span>
            </span>
          </StepHit>
        );
      })}
    </nav>
  );
}

export default Stepper;
export { resolveVisual as resolveStepperVisual };
