import React from 'react';
import PropTypes from 'prop-types';
import { Box } from '@mui/material';
import AppBreadcrumbs from '../appBreadcrumbs/appBreadcrumbs';
import PageBanner from '../pageBanner/pageBanner';
import PageLoadingState from '../pageLoadingState/pageLoadingState';
import './pageLayout.scss';

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
}) {
  return (
    <Box className={['ntq-page', className].filter(Boolean).join(' ')}>
      <Box className="ntq-page__shell">
        <AppBreadcrumbs items={breadcrumbsItems} current={breadcrumbsCurrent} />
        <PageBanner
          title={bannerTitle}
          description={bannerDescription}
          rightSlot={bannerRightSlot}
        />
        <Box className={['ntq-page__body', loading ? 'is-loading' : ''].filter(Boolean).join(' ')}>
          {loading ? (
            <PageLoadingState message={loadingMessage} minHeight="48vh" />
          ) : children}
        </Box>
      </Box>
    </Box>
  );
}

PageLayout.propTypes = {
  breadcrumbsItems: PropTypes.arrayOf(PropTypes.shape({ label: PropTypes.string.isRequired, to: PropTypes.string.isRequired })),
  breadcrumbsCurrent: PropTypes.node.isRequired,
  bannerTitle: PropTypes.string.isRequired,
  bannerDescription: PropTypes.node,
  bannerRightSlot: PropTypes.node,
  children: PropTypes.node,
  className: PropTypes.string,
  loading: PropTypes.bool,
  loadingMessage: PropTypes.string,
};

export default PageLayout;
