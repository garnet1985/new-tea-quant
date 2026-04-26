import React from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Stack,
  Typography,
} from '@mui/material';

function SectionField({ node, value, onChange, errors, emitChangeMeta, renderNode, context }) {
  const children = Array.isArray(node.children) ? node.children : [];
  const getChildKey = (child, index) => child?.name || child?.label || `${node.name || 'section'}-${index}`;

  return (
    <Accordion key={node.name} defaultExpanded={Boolean(node.defaultExpanded)} disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography fontWeight={600}>{node.label}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1.25}>
          {children.map((child, index) => (
            <React.Fragment key={getChildKey(child, index)}>
              {renderNode(child, value, onChange, errors, emitChangeMeta, context)}
            </React.Fragment>
          ))}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

export default SectionField;