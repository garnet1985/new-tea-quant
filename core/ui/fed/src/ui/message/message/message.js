import React from 'react';
import Icon from 'ui/icon/icon';
import {
  MESSAGE_COLORS,
  MESSAGE_STATUSES,
  MESSAGE_VARIANTS,
  pickToken,
} from 'ui/tokens';
import './style.scss';

/** 状态 → 固定图标（不可被 icon prop 覆盖） */
const STATUS_ICON = {
  success: { name: 'success', tone: 'success' },
  error: { name: 'cancel', tone: 'error' },
  warning: { name: 'warning', tone: 'warning' },
  info: { name: 'info', tone: 'cyan' },
};

/** 颜色模式 → 图标色调（仅当传入 icon 名时使用） */
const COLOR_ICON_TONE = {
  green: 'success',
  error: 'error',
  warning: 'warning',
  muted: 'muted',
  cyan: 'cyan',
  violet: 'violet',
};

/**
 * 消息条。
 * - variant=inline：圆角 + border + 底色，无左侧 bar
 * - variant=banner：左侧 bar、无圆角（header 下通栏）
 * - status：语义状态，图标固定不可改
 * - color：纯颜色（可与 status 二选一）；icon 可传入或省略
 *
 * @example
 * <Message status="success">已保存。</Message>
 * <Message status="info" variant="banner">说明通栏。</Message>
 * <Message color="violet">说明文案</Message>
 * <Message color="cyan" icon="settings">带自定义图标</Message>
 */
function Message({
  status = 'info',
  color,
  variant = 'inline',
  icon,
  onClose,
  className = '',
  style,
  children,
  ...rest
}) {
  const variantToken = pickToken(variant, MESSAGE_VARIANTS, 'inline');
  const colorToken = MESSAGE_COLORS.includes(color) ? color : null;
  const isColorMode = colorToken != null;
  const statusToken = isColorMode
    ? null
    : pickToken(status, MESSAGE_STATUSES, 'info');
  const accentKey = isColorMode ? colorToken : statusToken;

  const role = (!isColorMode && (statusToken === 'error' || statusToken === 'warning'))
    ? 'alert'
    : 'status';

  let iconNode = null;
  if (isColorMode) {
    if (icon != null && icon !== false) {
      if (typeof icon === 'string') {
        iconNode = (
          <Icon
            name={icon}
            size="xl"
            tone={COLOR_ICON_TONE[colorToken] || ''}
          />
        );
      } else {
        iconNode = icon;
      }
    }
  } else {
    const preset = STATUS_ICON[statusToken];
    iconNode = (
      <Icon name={preset.name} size="xl" tone={preset.tone} />
    );
  }

  const rootClass = [
    'ntq-message',
    `ntq-message--${variantToken}`,
    `ntq-message--${accentKey}`,
    isColorMode ? 'ntq-message--color' : 'ntq-message--status',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div
      className={rootClass}
      style={style}
      role={role}
      {...rest}
    >
      {iconNode ? (
        <span className="ntq-message__icon" aria-hidden="true">
          {iconNode}
        </span>
      ) : null}
      <div className="ntq-message__body">{children}</div>
      {typeof onClose === 'function' ? (
        <button
          type="button"
          className="ntq-message__close"
          aria-label="关闭"
          onClick={onClose}
        >
          <Icon name="cancel" size="md" tone="muted" />
        </button>
      ) : null}
    </div>
  );
}

export default Message;
