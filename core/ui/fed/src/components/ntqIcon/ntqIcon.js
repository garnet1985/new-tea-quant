import React from 'react';
import PropTypes from 'prop-types';
import { NTQ_ICON_MAP } from './ntqIconRegistry';
import './ntqIcon.scss';

const NtqIcon = React.forwardRef(function NtqIcon(props, ref) {
  const {
    name,
    size = 24,
    className: iconClassName = '',
    spin = false,
    tone = '',
    title: iconTitle = '',
    style,
    ...rest
  } = props;

  const Icon = NTQ_ICON_MAP[name];
  if (!Icon) {
    if (process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.warn(`[NtqIcon] unknown icon: ${name}`);
    }
    return null;
  }

  const { className: wrapClassName, ...spanProps } = rest;
  const px = Number(size) > 0 ? Number(size) : 24;
  const iconClass = [
    'ntq-icon',
    tone ? `ntq-icon--${tone}` : '',
    spin ? 'ntq-icon--spin' : '',
    name === 'expandMore' ? 'ntq-icon--expand-more' : '',
    iconClassName,
  ].filter(Boolean).join(' ');
  const wrapClass = ['ntq-icon-wrap', wrapClassName].filter(Boolean).join(' ');

  return (
    <span
      ref={ref}
      className={wrapClass}
      style={style}
      {...spanProps}
    >
      <Icon
        className={iconClass}
        width={px}
        height={px}
        aria-hidden={iconTitle ? undefined : true}
        role={iconTitle ? 'img' : undefined}
        aria-label={iconTitle || undefined}
        title={iconTitle || undefined}
      />
    </span>
  );
});

NtqIcon.displayName = 'NtqIcon';

NtqIcon.propTypes = {
  name: PropTypes.oneOf(Object.keys(NTQ_ICON_MAP)).isRequired,
  size: PropTypes.number,
  className: PropTypes.string,
  spin: PropTypes.bool,
  tone: PropTypes.oneOf(['muted', 'success', 'error', 'warning', 'disabled', '']),
  title: PropTypes.string,
  style: PropTypes.object,
};

export default NtqIcon;
export { NTQ_ICON_MAP };
