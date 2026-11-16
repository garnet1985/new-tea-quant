import React from 'react';
import { Box } from '@mui/material';
import Heading from 'ui/text/heading';
import Separator from 'ui/text/separator';

/**
 * 图鉴样例节奏（只走 gap，子项不叠 margin）：
 * - 默认块距：--ntq-stack = 1rem
 * - 大节之间：1.5rem
 * - 标题在正文流中再补上边距（Heading gap）
 * - 样例舞台不加全局黑框
 */

export function Showcase({ children }) {
  return <Box className="ui-prototype__showcase">{children}</Box>;
}

/** 编号大节：Heading，不加竖条 */
export function SampleDim({ title, children }) {
  return (
    <Box className="ui-prototype__sample-dim">
      <Heading level="h4" className="ui-prototype__sample-dim-title">
        {title}
      </Heading>
      <Box className="ui-prototype__sample-dim-body">{children}</Box>
    </Box>
  );
}

/** 小节：左文右线 + 下方 demo 舞台 */
export function SampleRow({ label, children, block = false }) {
  return (
    <Box className="ui-prototype__sample-row">
      {label ? (
        <Separator className="ui-prototype__sample-sep">{label}</Separator>
      ) : null}
      <Box
        className={[
          'ui-prototype__sample-stage',
          block ? 'ui-prototype__sample-stage--block' : '',
        ].filter(Boolean).join(' ')}
      >
        {children}
      </Box>
    </Box>
  );
}

/** 不适用说明：单独成行，留出呼吸 */
export function SampleNA({ children = '本组件无此参数。' }) {
  return (
    <Box className="ui-prototype__sample-na-wrap">
      <p className="ntq-caption ui-prototype__sample-na">{children}</p>
    </Box>
  );
}
