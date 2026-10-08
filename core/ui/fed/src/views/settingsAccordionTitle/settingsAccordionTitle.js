import React from 'react';
import TipLabel from 'views/tipLabel';

/** Accordion 标题行：统一字重，可选区块级 tooltip */
export default function SettingsAccordionTitle({ title, tooltip = '', context = {} }) {
  return (
    <TipLabel
      variant="title"
      tip={tooltip}
      shine={Boolean(context?.defaultTooltipShine)}
    >
      {title}
    </TipLabel>
  );
}
