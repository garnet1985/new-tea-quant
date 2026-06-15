import React from 'react';
import PropTypes from 'prop-types';
import { Box } from '@mui/material';
import AppBreadcrumbs from '../../components/appBreadcrumbs/appBreadcrumbs';
import '../../components/pageLayout/pageLayout.scss';
import './strategyDesignShell.scss';

/** 制定策略页壳：仅面包屑 + 正文（无 PageBanner） */
function StrategyDesignShell({ breadcrumbsItems, breadcrumbsCurrent, children, className }) {
  return (
    <Box className={['ntq-page', 'strategy-design-shell', className].filter(Boolean).join(' ')}>
      <Box className="ntq-page__shell">
        <AppBreadcrumbs items={breadcrumbsItems} current={breadcrumbsCurrent} />
        {children}
      </Box>
    </Box>
  );
}

StrategyDesignShell.propTypes = {
  breadcrumbsItems: PropTypes.arrayOf(
    PropTypes.shape({ label: PropTypes.string.isRequired, to: PropTypes.string.isRequired }),
  ),
  breadcrumbsCurrent: PropTypes.node.isRequired,
  children: PropTypes.node,
  className: PropTypes.string,
};

StrategyDesignShell.defaultProps = {
  breadcrumbsItems: [],
  children: null,
  className: '',
};

export default StrategyDesignShell;
