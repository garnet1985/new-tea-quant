import React from 'react';
import { Tooltip } from '@mui/material';
import Icon from 'ui/icon/icon';
import { HELP_TOOLTIP_VARIANTS, pickToken } from 'ui/tokens';
import HelpTooltipTransition, { HELP_TOOLTIP_TRANSITION_MS } from './helpTooltipTransition';
import './style.scss';

const VARIANT_ICON = {
  help: 'help',
  info: 'info',
  warning: 'warning',
};

const VARIANT_LABEL = {
  help: '帮助说明',
  info: '更多信息',
  warning: '注意',
};

/**
 * 统一说明 Tooltip。
 * help / info / warning 图标 + 可选 shine + 浮入动画。图标固定 md。
 * CSS 根类暂仍为 `.ntq-help-tooltip*`（后续可改为 `ui-help-tooltip`）。
 *
 * @example
 * <HelpTooltip title="字段含义说明" />
 * <HelpTooltip title="注意配额" variant="warning" shine />
 */
function HelpTooltip({
  title,
  variant = 'help',
  shine = false,
  placement = 'top',
  ariaLabel = '',
  className = '',
}) {
  const variantToken = pickToken(variant, HELP_TOOLTIP_VARIANTS, 'help');
  const iconName = VARIANT_ICON[variantToken];

  const triggerClass = [
    'ntq-help-tooltip-trigger',
    `ntq-help-tooltip-trigger--${variantToken}`,
    shine ? 'ntq-help-tooltip-trigger--shine' : '',
    className,
  ].filter(Boolean).join(' ');

  if (!title) {
    return null;
  }

  return (
    <Tooltip
      title={title}
      arrow
      placement={placement}
      describeChild
      TransitionComponent={HelpTooltipTransition}
      TransitionProps={{ timeout: HELP_TOOLTIP_TRANSITION_MS, placement }}
      classes={{
        popper: 'ntq-help-tooltip__popper',
        tooltip: 'ntq-help-tooltip__tooltip',
        arrow: 'ntq-help-tooltip__arrow',
      }}
    >
      <span
        className={triggerClass}
        role="button"
        tabIndex={0}
        aria-label={ariaLabel || VARIANT_LABEL[variantToken]}
      >
        <span className="ntq-help-tooltip-trigger__icon" aria-hidden>
          <Icon name={iconName} size="md" />
        </span>
      </span>
    </Tooltip>
  );
}

export default HelpTooltip;
