import React from 'react';
import { Tooltip } from '@mui/material';
import Icon from 'ui/icon/icon';
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
 * - tooltip：悬停说明（立刻弹出；仅有文案时启用）
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
  tooltip = '',
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
      iconNode = <Icon name={icon} size="sm" />;
    } else {
      iconNode = icon;
    }
  }

  const tip = String(tooltip || '').trim();
  const rootClass = [
    'ntq-tag',
    `ntq-tag--${variantToken}`,
    `ntq-tag--${sizeToken}`,
    `ntq-tag--${accentKey}`,
    tip ? 'ntq-tag--with-tooltip' : '',
    className,
  ].filter(Boolean).join(' ');

  const tag = (
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
          <Icon name="cancel" size="sm" />
        </button>
      ) : null}
    </span>
  );

  if (!tip) {
    return tag;
  }

  return (
    <Tooltip title={tip} arrow enterDelay={0} leaveDelay={0} describeChild>
      {tag}
    </Tooltip>
  );
}

export default Tag;
