import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Button,
  Card,
  CardContent,
  Stack,
  Typography,
} from '@mui/material';
import PageLayout from '../../components/pageLayout/pageLayout';
import './welcomePage.scss';

const highlights = [
  {
    title: '分层研究，而不是一条净值曲线',
    body: '把机会发现、价格捕获和资金投放拆开验证，避免被一条好看的回测曲线掩盖底层问题。',
  },
  {
    title: '为个人电脑优化',
    body: '动态调度 CPU 与内存，全市场枚举不必一上来就上云。',
  },
  {
    title: '贴近真实交易约束',
    body: '默认处理幸存者偏差、涨跌停无法成交、T+1 等容易让回测失真的规则。NTQ 做投研与信号，不直接接入实盘。',
  },
];

function WelcomePage() {
  return (
    <PageLayout
      className="welcome-page"
      breadcrumbsItems={[]}
      breadcrumbsCurrent="欢迎"
      bannerTitle="欢迎使用 New Tea Quant"
      bannerDescription="面向个人开发者的轻量量化研究框架：验证策略、扫描信号，把时间留给研究而不是配环境。"
    >
      <Stack spacing={2} sx={{ mt: 1 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
          <Button component={RouterLink} to="/strategy-design" variant="contained">
            制定策略
          </Button>
          <Button component={RouterLink} to="/scan" variant="outlined">
            策略选股
          </Button>
          <Button component={RouterLink} to="/settings" variant="text">
            设置
          </Button>
        </Stack>

        {highlights.map((item) => (
          <Card key={item.title} variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 0.5 }}>
                {item.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {item.body}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Stack>
    </PageLayout>
  );
}

export default WelcomePage;
