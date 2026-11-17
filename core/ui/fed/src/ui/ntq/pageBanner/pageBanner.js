import React from 'react';
import './style.scss';

/**
 * NTQ 页头 Banner：大标题 + 可选说明 + 右侧操作槽。
 *
 * @example
 * <PageBanner title="策略列表" description="管理已导入的策略包。" />
 * <PageBanner title="设置" rightSlot={<NtqButton>保存</NtqButton>} />
 */
function PageBanner({
  title,
  description = null,
  rightSlot = null,
  className = '',
  ...rest
}) {
  const rootClass = ['ntq-page-banner', className].filter(Boolean).join(' ');

  return (
    <header className={rootClass} {...rest}>
      <div className="ntq-page-banner__inner">
        <div className="ntq-page-banner__row">
          <h1 className="ntq-page-banner__title">{title}</h1>
          {rightSlot ? (
            <div className="ntq-page-banner__right">{rightSlot}</div>
          ) : null}
        </div>
        {description ? (
          <div className="ntq-page-banner__desc ntq-muted">{description}</div>
        ) : null}
      </div>
    </header>
  );
}

export default PageBanner;
