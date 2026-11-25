import React from 'react';
import './style.scss';

/**
 * 引用块（固定样式）：白竖条 + 轻白底 + 四面缩进 + 斜体。
 * 无 size / padding / color 变体。说明/提示用 TextBlock。
 *
 * @example
 * <Quote>优先用语义 token，不要在调用处写死像素。</Quote>
 */
function Quote({
  className = '',
  style,
  children,
  ...rest
}) {
  const rootClass = ['ntq-quote', className].filter(Boolean).join(' ');

  return (
    <blockquote className={rootClass} style={style} {...rest}>
      <div className="ntq-quote__body">{children}</div>
    </blockquote>
  );
}

export default Quote;
