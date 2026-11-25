import React from 'react';
import AppBreadcrumbs from 'ntq-ui/appBreadcrumbs';
import PageBanner from 'ntq-ui/pageBanner';
import Loading from 'ui/progress/loading';
import './style.scss';

/**
 * 标准页壳：面包屑 + Banner + 正文（可选整页 Loading）。
 *
 * @example
 * <PageLayout
 *   breadcrumbsItems={[{ label: '制定策略', to: '/strategy-design' }]}
 *   breadcrumbsCurrent="设置"
 *   bannerTitle="设置"
 *   bannerDescription="…"
 * >
 *   {children}
 * </PageLayout>
 */
function PageLayout({
  breadcrumbsItems = [],
  breadcrumbsCurrent,
  bannerTitle,
  bannerDescription = null,
  bannerRightSlot = null,
  children = null,
  className = '',
  loading = false,
  loadingMessage = '正在加载…',
  showBreadcrumbs = true,
  showBanner = true,
}) {
  const rootClass = ['ntq-page', className].filter(Boolean).join(' ');
  const bodyClass = [
    'ntq-page__body',
    loading ? 'is-loading' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass}>
      <div className="ntq-page__shell">
        {showBreadcrumbs ? (
          <AppBreadcrumbs items={breadcrumbsItems} current={breadcrumbsCurrent} />
        ) : null}
        {showBanner ? (
          <PageBanner
            title={bannerTitle}
            description={bannerDescription}
            rightSlot={bannerRightSlot}
          />
        ) : null}
        <div className={bodyClass}>
          {loading ? (
            <Loading variant="page" message={loadingMessage} />
          ) : children}
        </div>
      </div>
    </div>
  );
}

export default PageLayout;
