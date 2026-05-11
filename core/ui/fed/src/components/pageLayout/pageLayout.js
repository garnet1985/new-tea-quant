import React from 'react';
import PropTypes from 'prop-types';
import { Box } from '@mui/material';
import AppBreadcrumbs from '../appBreadcrumbs/appBreadcrumbs';
import PageBanner from '../pageBanner/pageBanner';
import './pageLayout.scss';

function PageLayout({
  breadcrumbsItems,
  breadcrumbsCurrent,
  bannerTitle,
  bannerDescription,
  bannerRightSlot,
  bannerBackgroundImage,
  children,
  className,
}) {
  return (
    <Box className={['ntq-page', className].filter(Boolean).join(' ')}>
      <AppBreadcrumbs items={breadcrumbsItems} current={breadcrumbsCurrent} />
      <PageBanner
        title={bannerTitle}
        description={bannerDescription}
        rightSlot={bannerRightSlot}
        backgroundImage={bannerBackgroundImage}
      />
      <Box className="ntq-page__body">
        {children}
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
  bannerBackgroundImage: PropTypes.string,
  children: PropTypes.node,
  className: PropTypes.string,
};

PageLayout.defaultProps = {
  breadcrumbsItems: [],
  bannerDescription: null,
  bannerRightSlot: null,
  bannerBackgroundImage: '',
  children: null,
  className: '',
};

export default PageLayout;

