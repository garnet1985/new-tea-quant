import React from 'react';
import { Typography } from '@mui/material';
import NtqHelpTooltip from 'views/ntqHelpTooltip';
import './style.scss';

const TEXT = {
  section: {
    variant: 'subtitle2',
    className: 'ntq-tip-label__text',
  },
  caption: {
    variant: 'caption',
    color: 'text.secondary',
    className: 'ntq-tip-label__text',
  },
  field: {
    variant: 'body2',
    className: 'ntq-tip-label__text',
  },
  title: {
    component: 'span',
    fontWeight: 600,
    className: 'ntq-tip-label__text ntq-tip-label__text--title',
  },
};

/**
 * 一行文字加可选说明。`variant` 只改字号：区块、说明、表单、手风琴。
 * `shine` 默认关。已有自己字号的标题用 `textClassName`，不再套预设。
 */
function TipLabel({
  children,
  tip = '',
  shine = false,
  variant = 'section',
  className = '',
  textClassName = '',
  component,
  placement,
  iconSize,
}) {
  const hasText = children != null && children !== '';
  if (!hasText && !tip) return null;

  const rootClass = ['ntq-tip-label', className].filter(Boolean).join(' ');
  const preset = TEXT[variant] || TEXT.section;
  const textClass = textClassName || preset.className;

  return (
    <div className={rootClass}>
      {hasText ? (
        <Typography
          variant={textClassName ? undefined : preset.variant}
          color={textClassName ? undefined : preset.color}
          fontWeight={textClassName ? undefined : preset.fontWeight}
          component={component || preset.component || 'span'}
          className={textClass}
        >
          {children}
        </Typography>
      ) : null}
      {tip ? (
        <NtqHelpTooltip
          title={tip}
          shine={shine}
          placement={placement}
          iconSize={iconSize}
        />
      ) : null}
    </div>
  );
}

export default TipLabel;
