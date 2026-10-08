import React from 'react';
import NtqIcon from 'views/ntqIcon';
import './style.scss';

/**
 * 彩虹描边按钮。
 * shape：circle 圆形，pill 圆角矩形。
 * ring：spin 色带转动，still 静止渐变，plain 灰边、不闪。
 * glow 是外圈光晕。shimmer 是文字上的色带流动。quiet 把光晕压暗（对话打开时）。
 * icon：play / refresh，色带裁进图标。mark：help 问号，ai 字标。
 */
function RainbowButton({
  shape = 'circle',
  size = 'sm',
  ring = 'spin',
  glow = false,
  quiet = false,
  shimmer = false,
  icon = '',
  mark = '',
  className = '',
  children,
  type = 'button',
  ...rest
}) {
  const rootClass = [
    'ntq-rainbow-button',
    `ntq-rainbow-button--${shape}`,
    `ntq-rainbow-button--${size}`,
    `ntq-rainbow-button--ring-${ring}`,
    glow ? 'ntq-rainbow-button--glow' : '',
    quiet ? 'ntq-rainbow-button--quiet' : '',
    className,
  ].filter(Boolean).join(' ');

  const glyph = icon === 'play' || icon === 'refresh' ? (
    <span className={`ntq-rainbow-button__glyph ntq-rainbow-button__glyph--${icon}`} aria-hidden>
      <span className="ntq-rainbow-button__glyph-aurora" />
    </span>
  ) : null;

  let face = glyph;
  if (mark === 'help') {
    face = <span className="ntq-rainbow-button__mark" aria-hidden>?</span>;
  } else if (mark === 'ai') {
    face = (
      <span className="ntq-rainbow-button__ai" aria-hidden>
        <span className="ntq-rainbow-button__spark ntq-rainbow-button__spark--a" />
        <span className="ntq-rainbow-button__spark ntq-rainbow-button__spark--b" />
        <span className="ntq-rainbow-button__ai-text">AI</span>
      </span>
    );
  } else if (children != null && children !== '') {
    const labelClass = [
      'ntq-rainbow-button__label',
      shimmer ? 'ntq-rainbow-button__label--shimmer' : '',
    ].filter(Boolean).join(' ');
    face = ring === 'plain' ? children : (
      <>
        {glyph}
        <span className={labelClass}>{children}</span>
      </>
    );
  } else if (icon === 'cancel') {
    face = <NtqIcon name="cancel" size={22} />;
  }

  const showClip = shape === 'pill' && ring === 'spin';

  return (
    <button type={type} className={rootClass} {...rest}>
      {glow ? <span className="ntq-rainbow-button__glow" aria-hidden /> : null}
      {showClip ? <span className="ntq-rainbow-button__aurora" aria-hidden /> : null}
      {!showClip && ring !== 'plain' ? <span className="ntq-rainbow-button__ring" aria-hidden /> : null}
      <span className={showClip ? 'ntq-rainbow-button__inner' : 'ntq-rainbow-button__face'}>
        {face}
      </span>
    </button>
  );
}

export default RainbowButton;
