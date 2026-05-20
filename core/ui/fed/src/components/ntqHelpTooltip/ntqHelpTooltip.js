import React from 'react';
import PropTypes from 'prop-types';
import { Tooltip } from '@mui/material';
import NtqIcon from '../ntqIcon/ntqIcon';
import NtqHelpTooltipTransition, { NTQ_HELP_TOOLTIP_TRANSITION_MS } from './ntqHelpTooltipTransition';
import './ntqHelpTooltip.scss';

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
 * 统一说明 Tooltip：help / info / warning 图标（SVG 自带外圈，不再叠 CSS 描边）+ 可选 shine + 浮入动画。
 */
function NtqHelpTooltip({
  title,
  variant = 'help',
  shine = false,
  placement = 'top',
  iconSize = 20,
  ariaLabel,
  className = '',
}) {
  const iconName = VARIANT_ICON[variant] || VARIANT_ICON.help;

  const triggerClass = [
    'ntq-help-tooltip-trigger',
    `ntq-help-tooltip-trigger--${variant}`,
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
      TransitionComponent={NtqHelpTooltipTransition}
      TransitionProps={{ timeout: NTQ_HELP_TOOLTIP_TRANSITION_MS, placement }}
      classes={{
        popper: 'ntq-help-tooltip__popper',
        tooltip: 'ntq-help-tooltip__tooltip',
        arrow: 'ntq-help-tooltip__arrow',
      }}
    >
      <span
        className={triggerClass}
        style={{ '--ntq-help-tooltip-size': `${iconSize}px` }}
        role="button"
        tabIndex={0}
        aria-label={ariaLabel || VARIANT_LABEL[variant] || VARIANT_LABEL.help}
      >
        <span className="ntq-help-tooltip-trigger__icon" aria-hidden>
          <NtqIcon name={iconName} size={iconSize} />
        </span>
      </span>
    </Tooltip>
  );
}

NtqHelpTooltip.defaultProps = {
  variant: 'help',
  shine: false,
  placement: 'top',
  iconSize: 20,
  ariaLabel: '',
  className: '',
};

NtqHelpTooltip.propTypes = {
  title: PropTypes.node,
  /** 默认 ``help``（问号）；``info`` / ``warning`` 需显式传入 */
  variant: PropTypes.oneOf(['help', 'info', 'warning']),
  shine: PropTypes.bool,
  placement: PropTypes.oneOf([
    'top',
    'top-start',
    'top-end',
    'bottom',
    'bottom-start',
    'bottom-end',
    'left',
    'left-start',
    'left-end',
    'right',
    'right-start',
    'right-end',
  ]),
  iconSize: PropTypes.number,
  ariaLabel: PropTypes.string,
  className: PropTypes.string,
};

export default NtqHelpTooltip;
