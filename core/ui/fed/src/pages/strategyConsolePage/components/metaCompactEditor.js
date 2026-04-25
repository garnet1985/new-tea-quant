import React from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  Stack,
  Switch,
  Typography,
} from '@mui/material';

function MetaCompactEditor({
  sectionTitle,
  value,
  onChange,
  defaultExpanded = false,
}) {
  const meta = value || {};
  const name = meta.name || '--';
  const description = meta.description || '--';
  const enabled = Boolean(meta.is_enabled);

  return (
    <Accordion defaultExpanded={defaultExpanded} disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography fontWeight={600}>{sectionTitle}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 1,
            }}
          >
            <Typography variant="body1" fontWeight={600} sx={{ minWidth: 0 }}>
              {name}
            </Typography>
            <Stack direction="row" alignItems="center" spacing={0.5}>
              <Switch
                size="small"
                checked={enabled}
                onChange={(e) => {
                  if (!onChange) return;
                  onChange({ ...meta, is_enabled: e.target.checked });
                }}
              />
              <Chip
                size="small"
                color={enabled ? 'success' : 'default'}
                label={enabled ? '已启用' : '已禁用'}
              />
            </Stack>
          </Box>
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

export default MetaCompactEditor;
