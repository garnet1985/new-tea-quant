import React from 'react';
import './style.scss';

const VARIANTS = ['glass', 'soft'];

/**
 * 多行代码块（等宽、可滚动）。
 * 样式只收 variant：默认科技玻璃 glass，变种 soft。
 * language 落在内边距带内，不与代码重叠；暂不驱动高亮。
 *
 * @example
 * <CodeBlock language="js">{`const x = 1;`}</CodeBlock>
 * <CodeBlock variant="soft">{`npm run start`}</CodeBlock>
 */
function CodeBlock({
  language = '',
  variant = 'glass',
  className = '',
  style,
  children,
  ...rest
}) {
  const variantToken = VARIANTS.includes(variant) ? variant : 'glass';
  const hasLang = Boolean(language);

  const rootClass = [
    'ntq-code-block',
    `ntq-code-block--${variantToken}`,
    hasLang ? 'ntq-code-block--has-lang' : '',
    className,
  ].filter(Boolean).join(' ');

  const code = typeof children === 'string' ? children.replace(/^\n/, '') : children;

  return (
    <div className={rootClass} style={style} {...rest}>
      {hasLang ? (
        <div className="ntq-code-block__meta" aria-hidden="true">
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
export { VARIANTS as CODE_BLOCK_VARIANTS };
