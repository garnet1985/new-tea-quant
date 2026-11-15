import React from 'react';
import { RADIUS_TOKENS, SPACE_TOKENS, SURFACE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

/**
 * 多行代码块原语（等宽、可滚动）。
 * 现阶段不做语法高亮；language 仅作标注，后续可接 highlight.js。
 *
 * @example
 * <CodeBlock>{`npm install`}</CodeBlock>
 * <CodeBlock language="js" surface="panel" radius="md">{`const x = 1;`}</CodeBlock>
 */
function CodeBlock({
  language = '',
  surface = 'panel',
  radius = 'md',
  padding = 'md',
  bordered = true,
  className = '',
  style,
  children,
  ...rest
}) {
  const surfaceToken = pickToken(surface, SURFACE_TOKENS, 'panel');
  const radiusToken = pickToken(radius, RADIUS_TOKENS, 'md');
  const paddingToken = pickToken(padding, SPACE_TOKENS, 'md');

  const rootClass = [
    'ntq-code-block',
    surfaceToken !== 'none' ? `ntq-code-block--surface-${surfaceToken}` : '',
    `ntq-code-block--radius-${radiusToken}`,
    `ntq-code-block--pad-${paddingToken}`,
    bordered ? 'ntq-code-block--bordered' : '',
    className,
  ].filter(Boolean).join(' ');

  const code = typeof children === 'string' ? children.replace(/^\n/, '') : children;

  return (
    <div className={rootClass} style={style} {...rest}>
      {language ? (
        <div className="ntq-code-block__meta">
          <span className="ntq-code-block__lang">{language}</span>
        </div>
      ) : null}
      <pre className="ntq-code-block__pre">
        <code className="ntq-code-block__code">{code}</code>
      </pre>
    </div>
  );
}

export default CodeBlock;
