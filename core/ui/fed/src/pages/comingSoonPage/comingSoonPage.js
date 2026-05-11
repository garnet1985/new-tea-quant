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
      breadcrumbsItems={[{ label: '策略工作台', to: '/strategy-workbench' }]}
      breadcrumbsCurrent={title}
      bannerTitle={title}
      bannerDescription={desc}
      bannerRightSlot={<Chip size="small" color="default" label="Coming soon" variant="outlined" />}
    >
      <Card variant="outlined" sx={{ mt: 2 }}>
        <CardContent>
          <Stack spacing={1.5}>
            <Typography color="text.secondary" variant="body2" component="p" sx={{ fontStyle: 'italic' }}>
              This feature is not available yet — we&apos;re working on it.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </PageLayout>
  );
}

export default ComingSoonPage;
