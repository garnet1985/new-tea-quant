import React from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

function SettingsFieldsEditor({
  sectionTitle,
  schema,
  value,
  onChange,
  defaultExpanded = false,
}) {
  const fields = Array.isArray(schema) ? schema : [];
  const sectionValue = value || {};

  return (
    <Accordion defaultExpanded={defaultExpanded} disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography fontWeight={600}>{sectionTitle}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1.5}>
          {fields.map((field) => {
            const fieldValue = sectionValue[field.key];
            if (field.type === 'boolean') {
              return (
                <Box key={field.key}>
                  <Typography variant="caption" color="text.secondary">
                    {field.displayNameZh}
                  </Typography>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 0.5 }}>
                    <Switch
                      size="small"
                      checked={Boolean(fieldValue)}
                      disabled={Boolean(field.readonly)}
                      onChange={(e) => {
                        if (field.readonly || !onChange) return;
                        onChange({ ...sectionValue, [field.key]: e.target.checked });
                      }}
                    />
                    <Chip
                      size="small"
                      color={Boolean(fieldValue) ? 'success' : 'default'}
                      label={Boolean(fieldValue) ? '已启用' : '已禁用'}
                    />
                  </Stack>
                </Box>
              );
            }

            if (field.readonly) {
              return (
                <Box key={field.key}>
                  <Typography variant="caption" color="text.secondary">
                    {field.displayNameZh}
                  </Typography>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 0.5 }}>
                    <Typography variant="body1" fontWeight={field.key === 'name' ? 600 : 400}>
                      {fieldValue || '--'}
                    </Typography>
                    {field.tooltipFromKey ? (
                      <Tooltip title={sectionValue?.[field.tooltipFromKey] || ''} arrow>
                        <InfoOutlinedIcon fontSize="small" color="action" />
                      </Tooltip>
                    ) : null}
                  </Stack>
                </Box>
              );
            }

            return (
              <TextField
                key={field.key}
                size="small"
                label={field.displayNameZh}
                value={fieldValue ?? ''}
                fullWidth
                onChange={(e) => {
                  if (!onChange) return;
                  onChange({ ...sectionValue, [field.key]: e.target.value });
                }}
              />
            );
          })}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

export default SettingsFieldsEditor;
