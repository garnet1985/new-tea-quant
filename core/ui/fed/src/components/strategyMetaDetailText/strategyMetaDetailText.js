import React from 'react';
import PropTypes from 'prop-types';
import { Box, Stack, Typography } from '@mui/material';
import StrategyDescriptionText from '../strategyDescriptionText/strategyDescriptionText';

function StrategyMetaDetailText({
  description,
  entryConditions,
  variant,
  color,
  className,
  empty,
  maxLines,
}) {
  const entries = Array.isArray(entryConditions)
    ? entryConditions.map((item) => String(item || '').trim()).filter(Boolean)
    : [];

  const hasDescription = Boolean(String(description || '').trim());
  const hasEntries = entries.length > 0;

  if (!hasDescription && !hasEntries) {
    if (empty == null || empty === '') return null;
    return (
      <Typography variant={variant} color={color} className={className}>
        {empty}
      </Typography>
    );
  }

  return (
    <Stack spacing={0.75} className={className}>
      {hasDescription ? (
        <StrategyDescriptionText
          text={description}
          variant={variant}
          color={color}
          empty=""
          maxLines={maxLines}
        />
      ) : null}
      {hasEntries ? (
        <Box>
          <Typography variant={variant} color={color} fontWeight={600} sx={{ mb: 0.25 }}>
            入场条件：
          </Typography>
          <Box component="ul" sx={{ m: 0, pl: 2.25 }}>
            {entries.map((line) => (
              <Typography
                key={line}
                component="li"
                variant={variant}
                color={color}
                sx={{ mb: 0.25 }}
              >
                {line}
              </Typography>
            ))}
          </Box>
        </Box>
      ) : null}
    </Stack>
  );
}

StrategyMetaDetailText.propTypes = {
  description: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.array]),
  entryConditions: PropTypes.arrayOf(PropTypes.string),
  variant: PropTypes.string,
  color: PropTypes.string,
  className: PropTypes.string,
  empty: PropTypes.node,
  maxLines: PropTypes.number,
};

StrategyMetaDetailText.defaultProps = {
  description: '',
  entryConditions: [],
  variant: 'body2',
  color: 'text.secondary',
  className: '',
  empty: '暂无策略描述',
  maxLines: null,
};

export default StrategyMetaDetailText;
