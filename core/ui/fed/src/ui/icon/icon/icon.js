import React from 'react';
import { ICON_SIZE_TOKENS, ICON_TONE_TOKENS, pickToken } from 'ui/tokens';
import { ICON_MAP } from './iconRegistry';
import './style.scss';

/**
 * 图标原语。size / tone 只用语义 token。
 * CSS 根类暂仍为 `.ntq-icon`（后续可改为 `ui-icon`）。
 *
 * @example
 * <Icon name="add" size="md" />
 * <Icon name="success" size="lg" tone="success" />
 * <Icon name="refresh" size="md" spin />
 */
const Icon = React.forwardRef(function Icon(props, ref) {
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

  const Svg = ICON_MAP[name];
  if (!Svg) {
    if (process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.warn(`[Icon] unknown icon: ${name}`);
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
      <Svg
        className={iconClass}
        aria-hidden={iconTitle ? undefined : true}
        role={iconTitle ? 'img' : undefined}
        aria-label={iconTitle || undefined}
        title={iconTitle || undefined}
      />
    </span>
  );
});

Icon.displayName = 'Icon';

export default Icon;
export { ICON_MAP, ICON_NAMES, NTQ_ICON_MAP, NTQ_ICON_NAMES } from './iconRegistry';
