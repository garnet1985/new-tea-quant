import React from 'react';
import NtqIcon from 'ui/icon/ntqIcon';
import {
  TAG_COLORS,
  TAG_SIZE_TOKENS,
  TAG_STATUSES,
  TAG_VARIANTS,
  pickToken,
} from 'ui/tokens';
import './style.scss';

/**
 * 标签 / 状态小块。
 * - status：语义色（success/error/warning/info/neutral）
 * - color：装饰色（含紫）；与 status 二选一，有 color 走颜色模式
 * - variant：soft（浅底）/ outline / solid
 *
 * @example
 * <Tag status="success">已启用</Tag>
 * <Tag status="warning" variant="outline">待更新</Tag>
 * <Tag color="violet">策略</Tag>
 * <Tag status="neutral" onDelete={…}>可关闭</Tag>
 */
function Tag({
  status = 'neutral',
  color,
  variant = 'soft',
  size = 'sm',
  icon,
  onDelete,
  className = '',
  style,
  children,
  label,
  ...rest
}) {
  const variantToken = pickToken(variant, TAG_VARIANTS, 'soft');
  const sizeToken = pickToken(size, TAG_SIZE_TOKENS, 'sm');
  const colorToken = TAG_COLORS.includes(color) ? color : null;
  const isColorMode = colorToken != null;
  const statusToken = isColorMode
    ? null
    : pickToken(status, TAG_STATUSES, 'neutral');
  const accentKey = isColorMode ? colorToken : statusToken;

  const content = children != null && children !== false ? children : label;

  let iconNode = null;
  if (icon != null && icon !== false) {
    if (typeof icon === 'string') {
      iconNode = <NtqIcon name={icon} size="sm" />;
    } else {
      iconNode = icon;
    }
  }

  const rootClass = [
    'ntq-tag',
    `ntq-tag--${variantToken}`,
    `ntq-tag--${sizeToken}`,
    `ntq-tag--${accentKey}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <span className={rootClass} style={style} {...rest}>
      {iconNode ? (
        <span className="ntq-tag__icon" aria-hidden="true">
          {iconNode}
        </span>
      ) : null}
      <span className="ntq-tag__label">{content}</span>
      {typeof onDelete === 'function' ? (
        <button
          type="button"
          className="ntq-tag__delete"
          aria-label="移除"
          onClick={onDelete}
        >
          <NtqIcon name="cancel" size="sm" />
        </button>
      ) : null}
    </span>
  );
}

export default Tag;
