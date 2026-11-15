import React from 'react';
import {
  HEADING_BAR_TOKENS,
  HEADING_GAP_TOKENS,
  HEADING_LEVELS,
  HEADING_SUBTITLE_PLACEMENTS,
  HEADING_VARIANTS,
  pickToken,
} from 'ui/tokens';
import './style.scss';

/**
 * 标题原语。
 *
 * - level：h1–h5（标签 + 固定字号阶梯，不可单独改 font-size）
 * - variant：plain（默认）| bar（左侧竖条，上下/左内边距）
 * - subtitle + subtitlePlacement：below | inline
 * - gap：上下外边距，永远 上 > 下 > 普通段落间距；none 表示收紧
 *
 * @example
 * <Heading level="h1">页面标题</Heading>
 * <Heading level="h2" subtitle="说明" subtitlePlacement="below">区块</Heading>
 * <Heading level="h2" variant="bar" tone="cyan">带竖条</Heading>
 * <Heading level="h3" gap="none">侧栏紧凑</Heading>
 */
function Heading({
  level = 'h2',
  variant = 'plain',
  tone = 'cyan',
  subtitle = '',
  subtitlePlacement = 'below',
  gap = 'md',
  as,
  className = '',
  children,
  ...rest
}) {
  const levelToken = pickToken(level, HEADING_LEVELS, 'h2');
  const variantToken = pickToken(variant, HEADING_VARIANTS, 'plain');
  const gapToken = pickToken(gap, HEADING_GAP_TOKENS, 'md');
  const placeToken = pickToken(subtitlePlacement, HEADING_SUBTITLE_PLACEMENTS, 'below');
  const toneToken = HEADING_BAR_TOKENS.includes(tone) ? tone : 'cyan';
  const Tag = as || levelToken;
  const isBar = variantToken === 'bar';
  const hasSubtitle = Boolean(subtitle);
  const needsRoot = isBar || hasSubtitle;

  const titleClass = [
    'ntq-heading',
    `ntq-heading--${levelToken}`,
    !needsRoot ? `ntq-heading--gap-${gapToken}` : '',
    !needsRoot ? className : '',
  ].filter(Boolean).join(' ');

  const titleEl = (
    <Tag className={titleClass} {...(!needsRoot ? rest : {})}>
      {hasSubtitle && placeToken === 'inline' ? (
        <span className="ntq-heading__inline">
          <span className="ntq-heading__label">{children}</span>
          <span className="ntq-heading__subtitle ntq-heading__subtitle--inline">
            {subtitle}
          </span>
        </span>
      ) : (
        children
      )}
    </Tag>
  );

  if (!needsRoot) {
    return titleEl;
  }

  const rootClass = [
    'ntq-heading-root',
    `ntq-heading-root--${levelToken}`,
    `ntq-heading-root--gap-${gapToken}`,
    isBar ? 'ntq-heading-root--bar' : '',
    isBar ? `ntq-heading-root--tone-${toneToken}` : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} {...rest}>
      {titleEl}
      {hasSubtitle && placeToken === 'below' ? (
        <p className="ntq-heading__subtitle ntq-heading__subtitle--below">{subtitle}</p>
      ) : null}
    </div>
  );
}

export default Heading;
