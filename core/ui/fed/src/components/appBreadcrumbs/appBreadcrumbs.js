import React from 'react';
import PropTypes from 'prop-types';
import { Breadcrumbs, Link, Typography } from '@mui/material';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import { Link as RouterLink } from 'react-router-dom';
import './appBreadcrumbs.scss';

/**
 * Unified breadcrumbs for NTQ app pages.
 * items: [{ label, to }] ordered from root to leaf (excluding current).
 * current: string|node rendered as the last, non-clickable segment.
 */
function AppBreadcrumbs({ items, current, className }) {
  const safeItems = Array.isArray(items) ? items.filter((x) => x && x.label && x.to) : [];
  return (
    <Breadcrumbs
      separator={<NavigateNextIcon fontSize="small" />}
      className={['ntq-breadcrumbs', className].filter(Boolean).join(' ')}
    >
      {safeItems.map((it) => (
        <Link
          key={`${it.to}_${it.label}`}
          component={RouterLink}
          underline="hover"
          color="inherit"
          to={it.to}
        >
          {it.label}
        </Link>
      ))}
      <Typography color="text.primary" className="ntq-breadcrumbs__current">
        {current}
      </Typography>
    </Breadcrumbs>
  );
}

AppBreadcrumbs.propTypes = {
  items: PropTypes.arrayOf(PropTypes.shape({ label: PropTypes.string.isRequired, to: PropTypes.string.isRequired })),
  current: PropTypes.node.isRequired,
  className: PropTypes.string,
};

AppBreadcrumbs.defaultProps = {
  items: [],
  className: '',
};

export default AppBreadcrumbs;
