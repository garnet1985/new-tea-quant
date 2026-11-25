import React, { useId, useState } from 'react';
import Icon from 'ui/icon/icon';
import HelpTooltip from 'ui/message/helpTooltip';
import { pickToken } from 'ui/tokens';
import './style.scss';

export const ACCORDION_VARIANTS = ['panel', 'nested'];

/**
 * 折叠区块。panel=顶层拼缝；nested=内嵌圆角卡片。
 * 收起时仍挂载子树（对齐原 Accordion unmountOnExit:false），避免表单态丢失。
 *
 * @example
 * <Accordion title="全局设置" tooltip="说明" defaultExpanded>
 *   …
 * </Accordion>
 * <Accordion title="市场规则" variant="nested">…</Accordion>
 */
function Accordion({
  title,
  tooltip = '',
  shine = false,
  variant = 'panel',
  defaultExpanded = false,
  expanded,
  onExpandedChange,
  className = '',
  children,
  'data-ntq-help': helpTarget,
}) {
  const variantToken = pickToken(variant, ACCORDION_VARIANTS, 'panel');
  const reactId = useId();
  const panelId = `ntq-accordion-panel-${reactId.replace(/:/g, '')}`;
  const headerId = `ntq-accordion-header-${reactId.replace(/:/g, '')}`;

  const isControlled = expanded !== undefined && expanded !== null;
  const [innerExpanded, setInnerExpanded] = useState(Boolean(defaultExpanded));
  const open = isControlled ? Boolean(expanded) : innerExpanded;

  const setOpen = (next) => {
    if (!isControlled) setInnerExpanded(next);
    if (typeof onExpandedChange === 'function') onExpandedChange(next);
  };

  const toggle = () => setOpen(!open);

  const onSummaryKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggle();
    }
  };

  const rootClass = [
    'ntq-accordion',
    `ntq-accordion--${variantToken}`,
    open ? 'is-expanded' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} data-ntq-help={helpTarget || undefined}>
      <div
        id={headerId}
        className="ntq-accordion__summary"
        role="button"
        tabIndex={0}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={toggle}
        onKeyDown={onSummaryKeyDown}
      >
        <span className="ntq-accordion__title">
          <span className="ntq-accordion__title-text">{title}</span>
          {tooltip ? (
            <span
              className="ntq-accordion__tip"
              onClick={(event) => event.stopPropagation()}
              onKeyDown={(event) => event.stopPropagation()}
            >
              <HelpTooltip title={tooltip} shine={shine} placement="top" />
            </span>
          ) : null}
        </span>
        <span
          className={[
            'ntq-accordion__chevron',
            open ? 'ntq-accordion__chevron--open' : '',
          ].filter(Boolean).join(' ')}
          aria-hidden
        >
          <Icon name="expandMore" size="md" tone="muted" />
        </span>
      </div>
      <div
        id={panelId}
        role="region"
        aria-labelledby={headerId}
        hidden={!open}
        className="ntq-accordion__details"
      >
        {children}
      </div>
    </div>
  );
}

export default Accordion;
