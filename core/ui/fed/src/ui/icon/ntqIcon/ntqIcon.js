import React from 'react';
import { ICON_SIZE_TOKENS, ICON_TONE_TOKENS, pickToken } from 'ui/tokens';
import { NTQ_ICON_MAP } from './ntqIconRegistry';
import './style.scss';

/**
 * NTQ 图标原语。size / tone 只用语义 token。
 *
 * @example
 * <NtqIcon name="add" size="md" />
 * <NtqIcon name="success" size="lg" tone="success" />
 * <NtqIcon name="refresh" size="md" spin />
 */
const NtqIcon = React.forwardRef(function NtqIcon(props, ref) {
  const {
    name,
    size = 'md',
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

  const sizeToken = pickToken(size, ICON_SIZE_TOKENS, 'md');
  const toneToken = ICON_TONE_TOKENS.includes(tone) ? tone : '';
  const { className: wrapClassName, ...spanProps } = rest;

  const iconClass = [
    'ntq-icon',
    `ntq-icon--size-${sizeToken}`,
    toneToken ? `ntq-icon--${toneToken}` : '',
    spin ? 'ntq-icon--spin' : '',
    name === 'expandMore' ? 'ntq-icon--expand-more' : '',
    iconClassName,
  ].filter(Boolean).join(' ');

  const wrapClass = ['ntq-icon-wrap', wrapClassName].filter(Boolean).join(' ');

  return (
    <span ref={ref} className={wrapClass} style={style} {...spanProps}>
      <Icon
        className={iconClass}
        aria-hidden={iconTitle ? undefined : true}
        role={iconTitle ? 'img' : undefined}
        aria-label={iconTitle || undefined}
        title={iconTitle || undefined}
      />
    </span>
  );
});

NtqIcon.displayName = 'NtqIcon';

export default NtqIcon;
export { NTQ_ICON_MAP } from './ntqIconRegistry';
export { NTQ_ICON_NAMES } from './ntqIconRegistry';
