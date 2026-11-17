import React, { useEffect, useState } from 'react';
import { AVATAR_SIZE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

function letterOf(name) {
  const text = String(name || '').trim();
  if (!text) return '?';
  return text.slice(0, 1).toUpperCase();
}

/**
 * 头像：图片或姓名首字母回退。
 *
 * @example
 * <Avatar src="/a.png" name="Alice" />
 * <Avatar name="茶" size="lg" />
 */
function Avatar({
  src,
  name = '',
  alt = '',
  size = 'md',
  className = '',
  ...rest
}) {
  const sizeToken = pickToken(size, AVATAR_SIZE_TOKENS, 'md');
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [src]);

  const showImg = Boolean(src) && !failed;
  const rootClass = [
    'ntq-avatar',
    `ntq-avatar--${sizeToken}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <span
      className={rootClass}
      role={alt || name ? 'img' : undefined}
      aria-label={alt || name || undefined}
      aria-hidden={!(alt || name) ? true : undefined}
      {...rest}
    >
      {showImg ? (
        <img
          className="ntq-avatar__img"
          src={src}
          alt=""
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="ntq-avatar__letter">{letterOf(name)}</span>
      )}
    </span>
  );
}

export default Avatar;
