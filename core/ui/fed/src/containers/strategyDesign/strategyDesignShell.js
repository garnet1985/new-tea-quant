import React from 'react';
import PropTypes from 'prop-types';
import AppBreadcrumbs from 'ntq-ui/appBreadcrumbs';
import 'ntq-ui/pageLayout/style.scss';
import './strategyDesignShell.scss';

/** 制定策略页壳：仅面包屑 + 正文（无 PageBanner） */
function StrategyDesignShell({
  breadcrumbsItems = [],
  breadcrumbsCurrent,
  children = null,
  className = '',
}) {
  return (
    <div className={['ntq-page', 'strategy-design-shell', className].filter(Boolean).join(' ')}>
      <div className="ntq-page__shell">
        <AppBreadcrumbs items={breadcrumbsItems} current={breadcrumbsCurrent} />
        {children}
      </div>
    </div>
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

export default StrategyDesignShell;
