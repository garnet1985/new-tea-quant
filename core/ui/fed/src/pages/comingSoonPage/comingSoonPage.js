import React from 'react';
import { Box, Card, CardContent, Chip, Stack, Typography } from '@mui/material';
import PageLayout from '../../components/pageLayout/pageLayout';

/**
 * 导航中尚未实装的入口页：全宽由 MainLayout 的 main 已套 ntq-content-inner
 */
function ComingSoonPage({ title, description }) {
  const desc = description || '该功能正在规划中，即将与桌面端工作流对接。';
  return (
    <PageLayout
      className="coming-soon-page"
      breadcrumbsItems={[{ label: '策略实验室', to: '/strategy-workbench' }]}
      breadcrumbsCurrent={title}
      bannerTitle={title}
      bannerDescription={desc}
      bannerRightSlot={<Chip size="small" color="default" label="即将推出" variant="outlined" />}
    >
      <Card variant="outlined" sx={{ mt: 2 }}>
        <CardContent>
          <Stack spacing={1.5}>
            <Typography color="text.secondary" variant="body2" component="p" sx={{ fontStyle: 'italic' }}>
              敬请期待 - 我正在努力中...
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </PageLayout>
  );
}

export default ComingSoonPage;
