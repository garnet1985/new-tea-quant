import React from 'react';
import { TEXT_VARIANTS, pickToken } from 'ui/tokens';
import './style.scss';

const DEFAULT_TAG = {
  code: 'code',
  rainbow: 'span',
  accent: 'span',
};

/**
 * 行内特殊字形（不是通用正文包装器）。
 * 多行代码用 ui/text/codeBlock。
 *
 * @example
 * <Text variant="code">/dev/ui</Text>
 * <Text variant="rainbow">Brand</Text>
 * <Text variant="accent">高亮</Text>
 */
function Text({
  variant = 'code',
  as,
  className = '',
  children,
  ...rest
}) {
  const variantToken = pickToken(variant, TEXT_VARIANTS, 'code');
  const Comp = as || DEFAULT_TAG[variantToken] || 'span';
  const rootClass = [
    'ntq-text',
    `ntq-text--${variantToken}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <Comp className={rootClass} {...rest}>
      {children}
    </Comp>
  );
}

export default Text;
