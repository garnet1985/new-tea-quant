import React from 'react';
import PropTypes from 'prop-types';
import { Box, Typography } from '@mui/material';
import './pageBanner.scss';

function PageBanner({ title, description, backgroundImage, rightSlot }) {
  const style = backgroundImage
    ? { '--ntq-banner-bg': `url("${backgroundImage}")` }
    : undefined;

  return (
    <Box className="ntq-page-banner" style={style}>
      <Box className="ntq-page-banner__inner ntq-content-inner">
        <Box className="ntq-page-banner__row">
          <Typography variant="h5" className="ntq-page-banner__title">
            {title}
          </Typography>
          {rightSlot ? <Box className="ntq-page-banner__right">{rightSlot}</Box> : null}
        </Box>
        {description ? (
          <Typography variant="body2" className="ntq-page-banner__desc" color="text.secondary" component="div">
            {description}
          </Typography>
        ) : null}
      </Box>
    </Box>
  );
}

PageBanner.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.node,
  backgroundImage: PropTypes.string,
  rightSlot: PropTypes.node,
};

PageBanner.defaultProps = {
  description: null,
  backgroundImage: '',
  rightSlot: null,
};

export default PageBanner;

